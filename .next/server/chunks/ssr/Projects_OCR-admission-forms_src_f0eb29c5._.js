module.exports = {

"[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx [app-ssr] (ecmascript)": ((__turbopack_context__) => {
"use strict";

var { g: global, __dirname } = __turbopack_context__;
{
__turbopack_context__.s({
    "default": (()=>ErrorReporter)
});
var __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Projects/OCR-admission-forms/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react-jsx-dev-runtime.js [app-ssr] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Projects/OCR-admission-forms/node_modules/next/dist/server/route-modules/app-page/vendored/ssr/react.js [app-ssr] (ecmascript)");
"use client";
;
;
function ErrorReporter({ error, reset }) {
    /* ─ instrumentation shared by every route ─ */ const lastOverlayMsg = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRef"])("");
    const pollRef = (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useRef"])();
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        const inIframe = window.parent !== window;
        if (!inIframe) return;
        const send = (payload)=>window.parent.postMessage(payload, "*");
        const onError = (e)=>send({
                type: "ERROR_CAPTURED",
                error: {
                    message: e.message,
                    stack: e.error?.stack,
                    filename: e.filename,
                    lineno: e.lineno,
                    colno: e.colno,
                    source: "window.onerror"
                },
                timestamp: Date.now()
            });
        const onReject = (e)=>send({
                type: "ERROR_CAPTURED",
                error: {
                    message: e.reason?.message ?? String(e.reason),
                    stack: e.reason?.stack,
                    source: "unhandledrejection"
                },
                timestamp: Date.now()
            });
        const pollOverlay = ()=>{
            const overlay = document.querySelector("[data-nextjs-dialog-overlay]");
            const node = overlay?.querySelector("h1, h2, .error-message, [data-nextjs-dialog-body]") ?? null;
            const txt = node?.textContent ?? node?.innerHTML ?? "";
            if (txt && txt !== lastOverlayMsg.current) {
                lastOverlayMsg.current = txt;
                send({
                    type: "ERROR_CAPTURED",
                    error: {
                        message: txt,
                        source: "nextjs-dev-overlay"
                    },
                    timestamp: Date.now()
                });
            }
        };
        window.addEventListener("error", onError);
        window.addEventListener("unhandledrejection", onReject);
        pollRef.current = setInterval(pollOverlay, 1000);
        return ()=>{
            window.removeEventListener("error", onError);
            window.removeEventListener("unhandledrejection", onReject);
            pollRef.current && clearInterval(pollRef.current);
        };
    }, []);
    /* ─ extra postMessage when on the global-error route ─ */ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["useEffect"])(()=>{
        if (!error) return;
        window.parent.postMessage({
            type: "global-error-reset",
            error: {
                message: error.message,
                stack: error.stack,
                digest: error.digest,
                name: error.name
            },
            timestamp: Date.now(),
            userAgent: navigator.userAgent
        }, "*");
    }, [
        error
    ]);
    /* ─ ordinary pages render nothing ─ */ if (!error) return null;
    /* ─ global-error UI ─ */ return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("html", {
        "data-orchids-id": "src/components/ErrorReporter.tsx:99:4",
        "data-orchids-name": "html",
        children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("body", {
            "data-orchids-id": "src/components/ErrorReporter.tsx:100:6",
            "data-orchids-name": "body",
            className: "min-h-screen bg-background text-foreground flex items-center justify-center p-4",
            children: /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                "data-orchids-id": "src/components/ErrorReporter.tsx:101:8",
                "data-orchids-name": "div",
                className: "max-w-md w-full text-center space-y-6",
                children: [
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        "data-orchids-id": "src/components/ErrorReporter.tsx:102:10",
                        "data-orchids-name": "div",
                        className: "space-y-2",
                        children: [
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("h1", {
                                "data-orchids-id": "src/components/ErrorReporter.tsx:103:12",
                                "data-orchids-name": "h1",
                                className: "text-2xl font-bold text-destructive",
                                children: "Something went wrong!"
                            }, void 0, false, {
                                fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                                lineNumber: 103,
                                columnNumber: 13
                            }, this),
                            /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("p", {
                                "data-orchids-id": "src/components/ErrorReporter.tsx:106:12",
                                "data-orchids-name": "p",
                                className: "text-muted-foreground",
                                children: "An unexpected error occurred. Please try again fixing with Orchids"
                            }, void 0, false, {
                                fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                                lineNumber: 106,
                                columnNumber: 13
                            }, this)
                        ]
                    }, void 0, true, {
                        fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                        lineNumber: 102,
                        columnNumber: 11
                    }, this),
                    /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                        "data-orchids-id": "src/components/ErrorReporter.tsx:110:10",
                        "data-orchids-name": "div",
                        className: "space-y-2",
                        children: ("TURBOPACK compile-time value", "development") === "development" && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("details", {
                            "data-orchids-id": "src/components/ErrorReporter.tsx:112:14",
                            "data-orchids-name": "details",
                            className: "mt-4 text-left",
                            children: [
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("summary", {
                                    "data-orchids-id": "src/components/ErrorReporter.tsx:113:16",
                                    "data-orchids-name": "summary",
                                    className: "cursor-pointer text-sm text-muted-foreground hover:text-foreground",
                                    children: "Error details"
                                }, void 0, false, {
                                    fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                                    lineNumber: 113,
                                    columnNumber: 17
                                }, this),
                                /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("pre", {
                                    "data-orchids-id": "src/components/ErrorReporter.tsx:116:16",
                                    "data-orchids-name": "pre",
                                    className: "mt-2 text-xs bg-muted p-2 rounded overflow-auto",
                                    children: [
                                        error.message,
                                        error.stack && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            "data-orchids-id": "src/components/ErrorReporter.tsx:119:20",
                                            "data-orchids-name": "div",
                                            className: "mt-2 text-muted-foreground",
                                            children: error.stack
                                        }, void 0, false, {
                                            fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                                            lineNumber: 119,
                                            columnNumber: 21
                                        }, this),
                                        error.digest && /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$node_modules$2f$next$2f$dist$2f$server$2f$route$2d$modules$2f$app$2d$page$2f$vendored$2f$ssr$2f$react$2d$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["jsxDEV"])("div", {
                                            "data-orchids-id": "src/components/ErrorReporter.tsx:124:20",
                                            "data-orchids-name": "div",
                                            className: "mt-2 text-muted-foreground",
                                            children: [
                                                "Digest: ",
                                                error.digest
                                            ]
                                        }, void 0, true, {
                                            fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                                            lineNumber: 124,
                                            columnNumber: 21
                                        }, this)
                                    ]
                                }, void 0, true, {
                                    fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                                    lineNumber: 116,
                                    columnNumber: 17
                                }, this)
                            ]
                        }, void 0, true, {
                            fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                            lineNumber: 112,
                            columnNumber: 15
                        }, this)
                    }, void 0, false, {
                        fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                        lineNumber: 110,
                        columnNumber: 11
                    }, this)
                ]
            }, void 0, true, {
                fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
                lineNumber: 101,
                columnNumber: 9
            }, this)
        }, void 0, false, {
            fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
            lineNumber: 100,
            columnNumber: 7
        }, this)
    }, void 0, false, {
        fileName: "[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx",
        lineNumber: 99,
        columnNumber: 5
    }, this);
}
}}),
"[project]/Projects/OCR-admission-forms/src/app/global-error.tsx [app-ssr] (ecmascript)": ((__turbopack_context__) => {
"use strict";

var { g: global, __dirname } = __turbopack_context__;
{
__turbopack_context__.s({
    "default": (()=>__TURBOPACK__default__export__)
});
var __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$src$2f$components$2f$ErrorReporter$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/Projects/OCR-admission-forms/src/components/ErrorReporter.tsx [app-ssr] (ecmascript)");
"use client";
;
const __TURBOPACK__default__export__ = __TURBOPACK__imported__module__$5b$project$5d2f$Projects$2f$OCR$2d$admission$2d$forms$2f$src$2f$components$2f$ErrorReporter$2e$tsx__$5b$app$2d$ssr$5d$__$28$ecmascript$29$__["default"];
}}),

};

//# sourceMappingURL=Projects_OCR-admission-forms_src_f0eb29c5._.js.map