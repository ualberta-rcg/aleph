// Package proxycheck holds a deployment check, not a unit test. It verifies,
// against the real public URL, that the SAML proxy in front of the usage UI
// does not let a client choose its own identity.
//
// It is excluded from normal builds and from `go test ./...` by the
// "proxycheck" build tag, and it fails until the deployment is configured
// correctly. The session cookie is read without echo, so that it stays out
// of shell history and the process list:
//
//	export USAGE_UI_URL=https://usage.example.org
//	export USAGE_UI_EXPECT_USER=yourname
//	read -rs USAGE_UI_SESSION_COOKIE && export USAGE_UI_SESSION_COOKIE
//	go test -tags proxycheck -count=1 -v ./deploy/proxycheck/
//
// At the read prompt, paste the Cookie request header that your signed-in
// browser sends to the usage UI. See usage-ui/README.md ("Verify the proxy")
// for what each check means.
package proxycheck
