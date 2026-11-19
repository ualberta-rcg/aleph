// Command usage-ui serves Aleph users their own usage from the gateway ledger.
//
// Configuration is by environment variable; see usage-ui/README.md.
package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/ualberta-rcg/aleph/usage-ui/internal/auth"
	"github.com/ualberta-rcg/aleph/usage-ui/internal/history"
	"github.com/ualberta-rcg/aleph/usage-ui/internal/ledger"
	"github.com/ualberta-rcg/aleph/usage-ui/internal/web"
)

// env returns the environment variable key, or fallback when it is unset or
// empty. An empty value counts as unset because Kubernetes manifests often
// declare a variable as VAR: "" to show it exists (deploy/k8s/deployment.yaml
// does this for AUTH_TRUSTED_PROXIES and AUTH_ALLOW_ANY_PEER).
func env(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok && value != "" {
		return value
	}
	return fallback
}

func authenticator() (auth.Authenticator, error) {
	switch mode := env("AUTH_MODE", "header"); mode {
	case "header":
		// AUTH_STRIP_REALM removed any realm, which let alice@other-institution
		// sign in as the local alice. It is refused rather than ignored, so a
		// manifest that still sets it fails closed instead of silently
		// changing which identities are accepted.
		if _, set := os.LookupEnv("AUTH_STRIP_REALM"); set {
			return nil, errors.New("AUTH_STRIP_REALM is no longer supported: remove it, and if the proxy sends user@realm, set AUTH_REALM to that one realm (for example AUTH_REALM=ualberta.ca)")
		}
		return auth.NewHeader(auth.HeaderConfig{
			Name:           env("AUTH_HEADER", "X-Remote-User"),
			Realm:          env("AUTH_REALM", ""),
			TrustedProxies: env("AUTH_TRUSTED_PROXIES", ""),
			AllowAnyPeer:   env("AUTH_ALLOW_ANY_PEER", ""),
		})
	case "dev":
		// Two settings are required so dev mode is never enabled by accident.
		if env("AUTH_DEV_ALLOW", "") != "yes-this-is-not-production" {
			return nil, errors.New("AUTH_MODE=dev also needs AUTH_DEV_ALLOW=yes-this-is-not-production")
		}
		username := env("AUTH_DEV_USER", "alice")
		if !auth.ValidUsername(username) {
			return nil, errors.New("AUTH_DEV_USER is not a valid username")
		}
		log.Printf("WARNING: dev auth, every request is signed in as %q", username)
		return auth.Dev{Username: username}, nil
	default:
		return nil, errors.New("AUTH_MODE must be header or dev, got " + mode)
	}
}

func main() {
	log.SetFlags(log.LstdFlags | log.LUTC)

	root := env("USAGE_LOG_ROOT", "/var/log/aleph-usage")
	addr := env("LISTEN_ADDR", ":8080")
	interval, err := time.ParseDuration(env("REFRESH_INTERVAL", "60s"))
	if err != nil || interval < time.Second {
		log.Fatalf("REFRESH_INTERVAL must be a duration of at least 1s")
	}
	authn, err := authenticator()
	if err != nil {
		log.Fatal(err)
	}
	if info, err := os.Stat(root); err != nil || !info.IsDir() {
		log.Fatalf("USAGE_LOG_ROOT %q is not a readable directory", root)
	}

	// The gateway's rotation count (its GATEWAY_USAGE_LOG_BACKUPS). Unset, the
	// coverage check assumes any rotation may have deleted older records.
	backups, err := strconv.Atoi(env("USAGE_LOG_BACKUPS", "0"))
	if err != nil || backups < 0 {
		log.Fatalf("USAGE_LOG_BACKUPS must be a whole number of 0 or more")
	}
	src := ledger.NewFileSource(root, backups)

	// The pages read the ledger, plus the daily history when it is enabled.
	// The history saves finished days after each ledger refresh, on the
	// refresh goroutine, so it is set up before the ledger starts.
	var pages ledger.Source = src
	historyDir := env("USAGE_HISTORY_DIR", "")
	if historyDir != "" {
		keepDays, err := strconv.Atoi(env("USAGE_HISTORY_DAYS", "366"))
		if err != nil || keepDays < 1 {
			log.Fatalf("USAGE_HISTORY_DAYS must be a whole number of 1 or more")
		}
		store, err := history.Open(historyDir, keepDays)
		if err != nil {
			log.Fatal(err)
		}
		withHistory := history.Source{Ledger: src, Store: store}
		pages = withHistory
		src.OnRefresh = withHistory.Updater(time.Now)
		log.Printf("history: saving daily totals in %s, keeping %d days", historyDir, keepDays)
	} else {
		log.Printf("history: off (USAGE_HISTORY_DIR is unset), so usage the ledger rotates away is not kept")
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	go src.Run(ctx, interval)

	srv, err := web.New(pages, authn)
	if err != nil {
		log.Fatal(err)
	}
	srv.SiteName = env("SITE_TITLE", "Aleph")

	httpServer := &http.Server{
		Addr:              addr,
		Handler:           srv.Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
		MaxHeaderBytes:    64 << 10,
	}
	// ListenAndServe returns as soon as Shutdown starts, so main waits for
	// Shutdown to finish: in-flight responses get up to 10 seconds to drain.
	drained := make(chan struct{})
	go func() {
		defer close(drained)
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := httpServer.Shutdown(shutdownCtx); err != nil {
			log.Printf("shutdown: %v", err)
		}
	}()
	log.Printf("usage-ui listening on %s, ledger %s (backups %d), auth %s, refresh %s", addr, root, backups, authn.Mode(), interval)
	if err := httpServer.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
	<-drained
}
