package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"syscall"
	"time"

	"github.com/ualberta-rcg/aleph/portal/internal/auth"
	"github.com/ualberta-rcg/aleph/portal/internal/catalog"
	"github.com/ualberta-rcg/aleph/portal/internal/source"
	"github.com/ualberta-rcg/aleph/portal/internal/web"
)

func main() {
	log.SetFlags(log.LstdFlags | log.LUTC)
	if err := run(); err != nil {
		log.Printf("fatal: %v", err)
		os.Exit(1)
	}
}

func run() error {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	listenAddr := envOr("PORTAL_LISTEN_ADDR", ":8080")
	siteName := envOr("SITE_NAME", "Aleph")
	publicOrigin := strings.TrimSpace(os.Getenv("PUBLIC_ORIGIN"))
	sessionSecretRaw := os.Getenv("PORTAL_SESSION_SECRET")
	secret, err := auth.ParseSessionSecret(sessionSecretRaw)
	if err != nil {
		return err
	}

	sessionTTL, err := envDuration("SESSION_TTL", auth.DefaultSessionTTL)
	if err != nil {
		return err
	}
	denied := source.ParseDeniedIdentities(envOr("DENIED_IDENTITIES", source.DefaultDeniedIdentities))

	authMgr, err := auth.NewManager(auth.Config{
		SessionSecret:     secret,
		PublicOrigin:      publicOrigin,
		AllowInsecureHTTP: envBool("ALLOW_INSECURE_HTTP"),
		MockOIDCEnabled:   envBool("MOCK_OIDC_ENABLED"),
		AllowMockOIDC:     os.Getenv("ALLOW_MOCK_OIDC"),
		SessionTTL:        sessionTTL,
		DeniedIdentities:  denied,
		OIDC: auth.OIDCConfig{
			IssuerURL: os.Getenv("OIDC_ISSUER_URL"),
			ClientID:  os.Getenv("OIDC_CLIENT_ID"),
		},
	})
	if err != nil {
		return err
	}

	dataSourceMode := strings.ToLower(envOr("DATA_SOURCE", "ledger"))
	var backend source.Backend
	switch dataSourceMode {
	case "ledger":
		ledgerDir := envOr("LEDGER_DIR", "/var/log/aleph")
		if err := source.ValidateLedgerRoot(ledgerDir); err != nil {
			return err
		}
		refreshInterval, err := envDuration("LEDGER_REFRESH_INTERVAL", 30*time.Second)
		if err != nil {
			return err
		}
		ledgerBackups, err := envInt("LEDGER_BACKUPS", 5)
		if err != nil {
			return err
		}
		maxScans, err := envInt("PORTAL_MAX_CONCURRENT_SCANS", 1)
		if err != nil {
			return err
		}
		cacheTTL, err := envDuration("PORTAL_CACHE_TTL", 60*time.Second)
		if err != nil {
			return err
		}
		cacheMax, err := envInt("PORTAL_CACHE_MAX_ENTRIES", 64)
		if err != nil {
			return err
		}
		ledgerSrc := source.NewLedgerSource(source.LedgerConfig{
			Root:               ledgerDir,
			Backups:            ledgerBackups,
			DeniedIdentities:   denied,
			MaxConcurrentScans: maxScans,
			CacheTTL:           cacheTTL,
			MaxCacheEntries:    cacheMax,
		})
		go ledgerSrc.Run(ctx, refreshInterval)
		backend = ledgerSrc

	case "prometheus":
		promSrc, err := source.NewPrometheusSource(os.Getenv("PROMETHEUS_URL"))
		if err != nil {
			return err
		}
		backend = promSrc

	default:
		return errors.New("unsupported DATA_SOURCE (expected \"ledger\" or \"prometheus\")")
	}

	var tykValidator *auth.TykValidator
	tykURL := strings.TrimSpace(envOr("TYK_VALIDATE_URL", "http://gateway-svc-tyk-oss-tyk-gateway.tyk.svc.cluster.local:8080/v1/models"))
	if tykURL != "" && !strings.EqualFold(tykURL, "disabled") {
		tykTimeout, err := envDuration("TYK_VALIDATE_TIMEOUT", 5*time.Second)
		if err != nil {
			return err
		}
		tykValidator, err = auth.NewTykValidator(tykURL, tykTimeout)
		if err != nil {
			return err
		}
	}

	catalogURL := envOr("CATALOG_URL", "http://model-gateway.models.svc.cluster.local/v1/models?all=true")
	catalogTTL, err := envDuration("CATALOG_CACHE_TTL", 5*time.Minute)
	if err != nil {
		return err
	}
	var catClient *catalog.Client
	if catalogURL != "" && !strings.EqualFold(catalogURL, "disabled") {
		catClient = catalog.NewClient(catalogURL, catalogTTL)
	}

	privateNetOnly := !authMgr.SecureCookies()
	if strings.TrimSpace(os.Getenv("PORTAL_PRIVATE_NET_ONLY")) != "" {
		privateNetOnly = envBool("PORTAL_PRIVATE_NET_ONLY")
	}

	webSrv, err := web.New(web.Config{
		Source:         backend,
		Auth:           authMgr,
		Tyk:            tykValidator,
		Catalog:        catClient,
		SiteName:       siteName,
		APIBaseURL:     envOr("PUBLIC_API_BASE_URL", "https://inference.vulcan.alliancecan.ca"),
		WebUIURL:       envOr("PUBLIC_WEBUI_URL", "https://llm.vulcan.alliancecan.ca"),
		PrivateNetOnly: privateNetOnly,
	})
	if err != nil {
		return err
	}

	httpSrv := &http.Server{
		Addr:              listenAddr,
		Handler:           webSrv.Handler(),
		ReadHeaderTimeout: 10 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      60 * time.Second,
		IdleTimeout:       120 * time.Second,
		MaxHeaderBytes:    1 << 16,
	}

	errCh := make(chan error, 1)
	go func() {
		log.Printf("aleph-portal listening on %s (origin=%s auth=%s data_source=%s)",
			listenAddr, authMgr.PublicOrigin(), authMgr.ModeDescription(), backend.Mode())
		if err := httpSrv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			errCh <- err
		}
		close(errCh)
	}()

	select {
	case err := <-errCh:
		return err
	case <-ctx.Done():
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		return httpSrv.Shutdown(shutdownCtx)
	}
}

func envOr(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func envBool(key string) bool {
	switch strings.ToLower(strings.TrimSpace(os.Getenv(key))) {
	case "1", "true", "yes":
		return true
	default:
		return false
	}
}

func envDuration(key string, fallback time.Duration) (time.Duration, error) {
	raw := strings.TrimSpace(os.Getenv(key))
	if raw == "" {
		return fallback, nil
	}
	return time.ParseDuration(raw)
}

func envInt(key string, fallback int) (int, error) {
	raw := strings.TrimSpace(os.Getenv(key))
	if raw == "" {
		return fallback, nil
	}
	return strconv.Atoi(raw)
}
