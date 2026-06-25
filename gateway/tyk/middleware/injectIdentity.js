// Tyk JSVM post-auth middleware: inject authoritative identity headers.
// -----------------------------------------------------------------------------
// Runs AFTER Tyk authenticates the key. Stamps the caller's identity onto the
// upstream request as X-Aleph-* headers; the model-gateway reads these for every
// usage/accounting record (fairshare).
//
// IMPORTANT: we read identity from the key's `alias` and `tags`, NOT meta_data.
// Tyk OSS wipes session meta_data on the first request (it re-saves a thin
// session after rate-limiting), but alias + tags persist reliably. Keys are
// minted by scripts/tyk/tyk-admin.sh as:
//   alias = identity (service name or LDAP username)
//   tags  = ["aleph", "account:<account>", "type:<service|user>"]
//
// normalizeAuth.js already stripped any inbound X-Aleph-* headers, so the values
// set here are trustworthy. Requires enable_jsvm + a custom_middleware.post entry.

var injectIdentity = new TykJS.TykMiddleware.NewMiddleware({});

injectIdentity.NewProcessRequest(function(request, session) {
    var identity = (session && session.alias) ? session.alias : "";
    var account = identity;
    var itype = "service";

    var tags = (session && session.tags) ? session.tags : [];
    for (var i = 0; i < tags.length; i++) {
        var t = String(tags[i]);
        if (t.indexOf("account:") === 0) { account = t.substring(8); }
        else if (t.indexOf("type:") === 0) { itype = t.substring(5); }
    }

    request.SetHeaders["X-Aleph-Identity"] = String(identity);
    request.SetHeaders["X-Aleph-Account"] = String(account || identity);
    request.SetHeaders["X-Aleph-Identity-Type"] = String(itype);

    return injectIdentity.ReturnData(request, {});
});
