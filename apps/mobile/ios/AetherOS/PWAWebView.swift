import SwiftUI
import WebKit

/// High-Performance Native iOS WebKit Container for AetherOS PWA
struct PWAWebView: UIViewRepresentable {
    let url: URL
    @Binding var isLoading: Bool
    
    init(url: URL = URL(string: "https://ather-os.de5.net")!, isLoading: Binding<Bool> = .constant(false)) {
        self.url = url
        self._isLoading = isLoading
    }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        
        // Add Native Haptics Script Bridge
        let userContentController = WKUserContentController()
        userContentController.add(context.coordinator, name: "haptic")
        config.userContentController = userContentController
        
        let webView = WKWebView(frame: .zero, configuration: config)
        webView.navigationDelegate = context.coordinator
        webView.scrollView.bounces = true
        webView.scrollView.showsVerticalScrollIndicator = false
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.backgroundColor = UIColor(red: 0.01, green: 0.01, blue: 0.02, alpha: 1.0)
        webView.isOpaque = false
        
        // Set Custom User-Agent for Native App Detection
        webView.customUserAgent = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 AetherOS-iOS-Native"
        
        let request = URLRequest(url: url, cachePolicy: .useProtocolCachePolicy, timeoutInterval: 30.0)
        webView.load(request)
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        var parent: PWAWebView

        init(_ parent: PWAWebView) {
            self.parent = parent
        }

        func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
            DispatchQueue.main.async {
                self.parent.isLoading = true
            }
            // Auto dismiss loading indicator after 2.5 seconds fallback
            DispatchQueue.main.asyncAfter(deadline: .now() + 2.5) {
                self.parent.isLoading = false
            }
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            DispatchQueue.main.async {
                self.parent.isLoading = false
            }
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            DispatchQueue.main.async {
                self.parent.isLoading = false
            }
        }

        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            decisionHandler(.allow)
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            if message.name == "haptic" {
                HapticManager.shared.impact(.medium)
            }
        }
    }
}
