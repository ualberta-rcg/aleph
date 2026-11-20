package source

import (
	"context"
	"errors"
	"fmt"
	"net/url"
	"time"
)

// ErrPrometheusNotReady indicates that subject-labeled Prometheus usage series
// are not yet available, preventing model-only gateway /metrics counters from
// ever being mistaken for personal usage.
var ErrPrometheusNotReady = errors.New("prometheus backend: subject-scoped usage series are not enabled yet (use DATA_SOURCE=ledger)")

// PrometheusSource is the Backend seam for the upcoming private log-to-Prometheus
// pipeline. Until subject-labeled metrics are shipped into a private Prometheus
// instance, it fails closed rather than querying model-only gateway metrics.
type PrometheusSource struct {
	endpoint string
}

// NewPrometheusSource validates the target Prometheus base URL.
func NewPrometheusSource(rawURL string) (*PrometheusSource, error) {
	if rawURL == "" {
		return nil, errors.New("PROMETHEUS_URL is required when DATA_SOURCE=prometheus")
	}
	parsed, err := url.Parse(rawURL)
	if err != nil || (parsed.Scheme != "http" && parsed.Scheme != "https") || parsed.Host == "" {
		return nil, fmt.Errorf("invalid PROMETHEUS_URL %q", rawURL)
	}
	return &PrometheusSource{endpoint: rawURL}, nil
}

func (p *PrometheusSource) Mode() string                         { return "prometheus" }
func (p *PrometheusSource) Ready() bool                          { return false }
func (p *PrometheusSource) LookupKeyFP(_ KeyFP) (KeyMeta, bool)  { return KeyMeta{}, false }
func (p *PrometheusSource) EvictSubject(_ Subject)               {}
func (p *PrometheusSource) Endpoint() string                     { return p.endpoint }
func (p *PrometheusSource) Usage(_ context.Context, _ Subject, _, _ time.Time) (Report, error) {
	return Report{}, ErrPrometheusNotReady
}
