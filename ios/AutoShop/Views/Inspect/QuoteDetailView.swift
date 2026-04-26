import SwiftUI

#if os(iOS)

struct QuoteDetailView: View {
    let quoteId: String
    @State private var quote: QuoteResponse?
    @State private var isLoading = true
    @State private var isFinalizing = false
    @State private var finalizeResult: FinalizeQuoteResponse?
    @State private var errorMessage: String?

    private let api = SessionAPI()

    var body: some View {
        Group {
            if isLoading {
                ProgressView("Loading quote…").frame(maxHeight: .infinity)
            } else if let quote {
                quoteContent(quote)
            } else {
                ContentUnavailableView("Quote Not Found", systemImage: "doc.text.fill")
                    .frame(maxHeight: .infinity)
            }
        }
        .navigationTitle("Quote")
        .navigationBarTitleDisplayMode(.inline)
        .alert("Error", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: { Text(errorMessage ?? "") }
        .task { await loadQuote() }
    }

    // MARK: - Main content

    @ViewBuilder
    private func quoteContent(_ q: QuoteResponse) -> some View {
        List {
            // Status section
            Section {
                HStack {
                    Text("Status")
                    Spacer()
                    statusBadge(for: q.status)
                }
                LabeledContent("Total") {
                    Text(String(format: "$%.2f", q.total)).font(.headline)
                }
            }

            // Line items
            Section("Line Items") {
                if q.lineItems.isEmpty {
                    VStack(spacing: 8) {
                        Text("No line items yet.")
                            .font(.subheadline).foregroundStyle(.secondary)
                        Button("Refresh") { Task { await loadQuote() } }
                            .font(.subheadline)
                    }
                    .frame(maxWidth: .infinity).padding(.vertical, 6)
                } else {
                    ForEach(q.lineItems) { item in
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(item.description).font(.subheadline)
                                Text(item.type.capitalized).font(.caption).foregroundStyle(.secondary)
                            }
                            Spacer()
                            VStack(alignment: .trailing, spacing: 3) {
                                Text(String(format: "$%.2f", item.total)).font(.subheadline.bold())
                                Text("× \(Int(item.qty))").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                        .padding(.vertical, 2)
                    }
                }
            }

            // PDF actions (final state) — URL is deterministic, no need for in-memory result
            if q.status == "final" {
                Section("Documents") {
                    if let url = URL(string: "\(SessionAPI.baseURL)/quotes/\(q.quoteId)/pdf") {
                        ShareLink(item: url) {
                            Label("Open Estimate PDF", systemImage: "printer.fill")
                        }
                    }
                    if let token = finalizeResult?.shareToken {
                        Button {
                            UIPasteboard.general.string = "\(SessionAPI.baseURL)/r/\(token)"
                        } label: {
                            Label("Copy Report Link", systemImage: "link")
                        }
                    }
                }
            }

            // Finalize button (draft state only)
            if q.status == "draft" {
                Section {
                    Button {
                        Task { await finalizeQuote() }
                    } label: {
                        Group {
                            if isFinalizing {
                                HStack(spacing: 8) {
                                    ProgressView().tint(.white)
                                    Text("Generating PDFs…")
                                }
                            } else {
                                Label("Finalize Quote", systemImage: "checkmark.seal.fill")
                                    .font(.headline)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 4)
                    }
                    .disabled(isFinalizing)
                    .listRowBackground(Color.orange)
                    .foregroundStyle(.white)
                }
            }

            // Footer
            Section {
                Text("ID: \(q.quoteId.prefix(8))…")
                    .font(.caption.monospaced()).foregroundStyle(.tertiary)
            }
        }
    }

    // MARK: - Helpers

    private func statusBadge(for status: String) -> some View {
        Text(status == "final" ? "FINAL ✓" : status.uppercased())
            .font(.caption.bold())
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(status == "final" ? Color.green : Color.orange)
            .foregroundStyle(.white)
            .clipShape(Capsule())
    }

    private func loadQuote() async {
        do {
            quote = try await api.getQuote(quoteId: quoteId)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func finalizeQuote() async {
        isFinalizing = true
        defer { isFinalizing = false }
        do {
            let result = try await api.finalizeQuote(quoteId: quoteId)
            finalizeResult = result
            await loadQuote()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

#endif
