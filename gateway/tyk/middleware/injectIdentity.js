// Tyk JSVM post-auth middleware: inject authoritative identity headers.
// -----------------------------------------------------------------------------
// Runs AFTER Tyk authenticates the key, so the key's session metadata is
// available. We stamp the caller's identity onto the upstream request as
// X-Aleph-* headers; the model-gateway reads these for every usage/accounting
// record (fairshare). Because normalizeAuth.js already stripped any inbound
// X-Aleph-* headers, these values are trustworthy.
//
// Key metadata is set at key-creation time by scripts/tyk/tyk-admin.sh:
//   meta_data: { identity, account, identity_type }
//   - identity      : service name (e.g. openwebui) or LDAP username
//   - account       : billing/fairshare bucket (defaults to identity)
//   - identity_type : "service" | "user"
//
// Requires enable_jsvm: true and a custom_middleware.post entry pointing here.

var injectIdentity = new TykJS.TykMiddleware.NewMiddleware({});

injectIdentity.NewProcessRequest(function(request, session) {
    var md = (session && session.meta_data) ? session.meta_data : {};
    var identity = md.identity || md.username || "";
    var account = md.account || identity;
    var itype = md.identity_type || "service";

    request.SetHeaders["X-Aleph-Identity"] = String(identity);
    request.SetHeaders["X-Aleph-Account"] = String(account);
    request.SetHeaders["X-Aleph-Identity-Type"] = String(itype);

    return injectIdentity.ReturnData(request, {});
});
