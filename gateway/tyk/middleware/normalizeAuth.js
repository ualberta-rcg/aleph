// Tyk JSVM pre-auth middleware: catch-all API key normalization.
// -----------------------------------------------------------------------------
// Runs BEFORE Tyk's auth check. Clients send the same key under many different
// conventions depending on which SDK/provider they think they are talking to:
//   - OpenAI / Cohere : Authorization: Bearer <key>
//   - Anthropic       : x-api-key: <key>
//   - Azure OpenAI    : api-key: <key>
//   - Google          : x-goog-api-key: <key>
//   - query string    : ?api_key= / ?api-key= / ?key=
// We accept any of them, copy the key into the canonical Authorization: Bearer
// header that the API definition authenticates on, and strip any client-supplied
// X-Aleph-* identity headers so callers cannot spoof accounting identity (the
// authoritative values are injected post-auth by injectIdentity.js).
//
// Requires enable_jsvm: true (TYK_GW_ENABLEJSVM=true) and a custom_middleware.pre
// entry pointing at this file. See ww-overlays/overlays/.../54-tyk-middleware.yaml.

var normalizeAuth = new TykJS.TykMiddleware.NewMiddleware({});

normalizeAuth.NewProcessRequest(function(request, session) {
    function firstHeader(name) {
        var v = request.Headers[name];
        if (v && v.length) { return v[0]; }
        return "";
    }
    function firstParam(name) {
        if (!request.Params) { return ""; }
        var v = request.Params[name];
        if (!v) { return ""; }
        return (typeof v === "string") ? v : (v[0] || "");
    }

    var key = "";
    var auth = firstHeader("Authorization");
    if (auth) {
        var m = auth.match(/^[Bb]earer\s+(.+)$/);
        key = m ? m[1] : auth;
    }
    if (!key) { key = firstHeader("X-Api-Key"); }
    if (!key) { key = firstHeader("Api-Key"); }
    if (!key) { key = firstHeader("X-Goog-Api-Key"); }
    if (!key) { key = firstParam("api_key") || firstParam("api-key") || firstParam("key"); }

    if (key) {
        request.SetHeaders["Authorization"] = "Bearer " + key;
    }

    // Never let a caller assert their own identity to the accounting layer.
    request.DeleteHeaders.push("X-Aleph-Identity");
    request.DeleteHeaders.push("X-Aleph-Account");
    request.DeleteHeaders.push("X-Aleph-Identity-Type");

    return normalizeAuth.ReturnData(request, {});
});
