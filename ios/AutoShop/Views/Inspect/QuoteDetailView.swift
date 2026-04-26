import SwiftUI

#if os(iOS)

struct QuoteDetailView: View {
    let quoteId: String

    var body: some View {
        ContentUnavailableView("Loading Quote…", systemImage: "doc.text")
            .navigationTitle("Quote")
    }
}

#endif
