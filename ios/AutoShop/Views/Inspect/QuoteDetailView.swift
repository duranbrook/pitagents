import SwiftUI

#if os(iOS)

struct QuoteDetailView: View {
    let quoteId: String
    var presentedFromChat: Bool = false
    @Environment(\.dismiss) private var dismiss
    @State private var quote: QuoteResponse?
    @State private var isLoading = true
    @State private var isFinalizing = false
    @State private var isSaving = false
    @State private var isEditing = false
    @State private var editableItems: [EditableLineItem] = []
    @State private var finalizeResult: FinalizeQuoteResponse?
    @State private var errorMessage: String?

    var body: some View {
        Group {
            if isLoading {
                ProgressView("Loading quote…").frame(maxHeight: .infinity)
            } else if let quote {
                quoteContent(quote)
            } else {
                VStack(spacing: 12) {
                    Image(systemName: "doc.text.fill")
                        .font(.largeTitle).foregroundStyle(.secondary)
                    Text("Quote not found")
                        .font(.headline)
                    Text("ID: \(quoteId.prefix(8))…")
                        .font(.caption.monospaced()).foregroundStyle(.tertiary)
                    Button("Retry") { Task { await loadQuote() } }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .navigationTitle("Repair Quote")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { toolbarItems }
        .alert("Error", isPresented: Binding(
            get: { errorMessage != nil },
            set: { if !$0 { errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: { Text(errorMessage ?? "") }
        .task { await loadQuote() }
    }

    // MARK: - Toolbar

    @ToolbarContentBuilder
    private var toolbarItems: some ToolbarContent {
        ToolbarItem(placement: .navigationBarLeading) {
            if isEditing {
                Button("Cancel", role: .cancel) { cancelEditing() }
            } else if presentedFromChat {
                Button {
                    dismiss()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "chevron.left")
                        Text("Chat")
                    }
                }
            }
        }
        if quote?.status == "draft" {
            ToolbarItem(placement: .navigationBarTrailing) {
                if isEditing {
                    Button {
                        Task { await saveEdits() }
                    } label: {
                        if isSaving {
                            ProgressView().tint(.accentColor)
                        } else {
                            Text("Save").bold()
                        }
                    }
                    .disabled(isSaving)
                } else {
                    Button("Edit") { startEditing() }
                }
            }
        }
    }

    // MARK: - Main content

    @ViewBuilder
    private func quoteContent(_ q: QuoteResponse) -> some View {
        List {
            // Status + total header
            Section {
                HStack {
                    Text("Status")
                    Spacer()
                    statusBadge(for: q.status)
                }
                LabeledContent("Total") {
                    Text(String(format: "$%.2f", isEditing ? editableTotal : q.total))
                        .font(.headline.monospacedDigit())
                }
            }

            // Line items
            Section {
                if isEditing {
                    editingRows
                } else {
                    readonlyRows(q)
                }
            } header: {
                HStack {
                    Text("Line Items")
                    Spacer()
                    if !isEditing && q.status == "draft" {
                        Button("Edit") { startEditing() }
                            .font(.caption)
                    }
                }
            }

            // Add item buttons while editing
            if isEditing {
                Section("Add Item") {
                    Button {
                        editableItems.append(EditableLineItem(type: "labor"))
                    } label: {
                        Label("Add Labor", systemImage: "plus.circle")
                    }
                    Button {
                        editableItems.append(EditableLineItem(type: "part"))
                    } label: {
                        Label("Add Part", systemImage: "plus.circle")
                    }
                }
            }

            // PDF/share (final state)
            if q.status == "final" {
                Section("Documents") {
                    if let url = URL(string: "\(APIClient.shared.baseURL)/quotes/\(q.quoteId)/pdf") {
                        ShareLink(item: url) {
                            Label("Open Estimate PDF", systemImage: "printer.fill")
                        }
                    }
                    if let token = finalizeResult?.shareToken {
                        Button {
                            UIPasteboard.general.string = "\(APIClient.shared.baseURL)/r/\(token)"
                        } label: {
                            Label("Copy Customer Link", systemImage: "link")
                        }
                    }
                }
            }

            // Finalize (draft, not editing)
            if q.status == "draft" && !isEditing {
                Section {
                    Button {
                        Task { await doFinalizeQuote() }
                    } label: {
                        Group {
                            if isFinalizing {
                                HStack(spacing: 8) {
                                    ProgressView().tint(.white)
                                    Text("Generating PDF…")
                                }
                            } else {
                                Label("Finalize Quote", systemImage: "checkmark.seal.fill")
                                    .font(.headline)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 4)
                    }
                    .disabled(isFinalizing || q.lineItems.isEmpty)
                    .listRowBackground(q.lineItems.isEmpty ? Color(.systemGray4) : Color.orange)
                    .foregroundStyle(.white)
                }
            }

            Section {
                Text("ID: \(q.quoteId.prefix(8))…")
                    .font(.caption.monospaced()).foregroundStyle(.tertiary)
            }
        }
    }

    // MARK: - Read-only rows

    @ViewBuilder
    private func readonlyRows(_ q: QuoteResponse) -> some View {
        if q.lineItems.isEmpty {
            HStack(spacing: 12) {
                Image(systemName: "list.bullet.clipboard")
                    .foregroundStyle(.secondary)
                VStack(alignment: .leading, spacing: 2) {
                    Text("No line items yet")
                        .font(.subheadline).foregroundStyle(.secondary)
                    Text("Tap Edit to add labor and parts")
                        .font(.caption).foregroundStyle(.tertiary)
                }
            }
            .padding(.vertical, 6)
        } else {
            ForEach(q.lineItems) { item in
                HStack(alignment: .top, spacing: 12) {
                    Image(systemName: item.type == "labor" ? "wrench.and.screwdriver" : "shippingbox")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .frame(width: 18)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.description).font(.subheadline)
                        Text("\(item.type.capitalized)  ×\(formatQty(item.qty))  @ $\(String(format: "%.2f", item.unitPrice))")
                            .font(.caption).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(String(format: "$%.2f", item.total))
                        .font(.subheadline.bold().monospacedDigit())
                }
                .padding(.vertical, 2)
            }
        }
    }

    // MARK: - Editing rows

    @ViewBuilder
    private var editingRows: some View {
        ForEach($editableItems) { $item in
            EditableLineItemRow(item: $item)
        }
        .onDelete { editableItems.remove(atOffsets: $0) }
        .onMove  { editableItems.move(fromOffsets: $0, toOffset: $1) }
    }

    // MARK: - Helpers

    private var editableTotal: Double { editableItems.reduce(0) { $0 + $1.total } }

    private func startEditing() {
        guard let q = quote else { return }
        editableItems = q.lineItems.map { EditableLineItem(from: $0) }
        isEditing = true
    }

    private func cancelEditing() {
        isEditing = false
        editableItems = []
    }

    private func saveEdits() async {
        isSaving = true
        defer { isSaving = false }
        do {
            let items = editableItems.map { $0.toLineItem() }
            quote = try await APIClient.shared.updateQuoteLineItems(quoteId: quoteId, lineItems: items)
            isEditing = false
            editableItems = []
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func statusBadge(for s: String) -> some View {
        Text(s == "final" ? "FINAL ✓" : s.uppercased())
            .font(.caption.bold())
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(s == "final" ? Color.green : Color.orange)
            .foregroundStyle(.white)
            .clipShape(Capsule())
    }

    private func formatQty(_ qty: Double) -> String {
        qty.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(qty)) : String(format: "%.1f", qty)
    }

    private func loadQuote() async {
        do {
            quote = try await APIClient.shared.fetchQuote(id: quoteId)
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func doFinalizeQuote() async {
        isFinalizing = true
        defer { isFinalizing = false }
        do {
            finalizeResult = try await APIClient.shared.finalizeQuote(quoteId: quoteId)
            await loadQuote()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - EditableLineItemRow

private struct EditableLineItemRow: View {
    @Binding var item: EditableLineItem

    @State private var qtyText: String = ""
    @State private var priceText: String = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Picker("", selection: $item.type) {
                    Text("Labor").tag("labor")
                    Text("Part").tag("part")
                }
                .pickerStyle(.segmented)
                .frame(width: 130)

                TextField("Description", text: $item.description)
                    .font(.subheadline)
            }

            HStack(spacing: 6) {
                TextField(item.type == "labor" ? "Hrs" : "Qty", text: $qtyText)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 52)
                    .onChange(of: qtyText) { _, v in if let d = Double(v) { item.qty = d } }
                Text("×").foregroundStyle(.secondary)
                Text("$").foregroundStyle(.secondary)
                TextField("Unit price", text: $priceText)
                    .keyboardType(.decimalPad)
                    .multilineTextAlignment(.trailing)
                    .frame(width: 72)
                    .onChange(of: priceText) { _, v in if let d = Double(v) { item.unitPrice = d } }
                Spacer()
                Text(String(format: "= $%.2f", item.total))
                    .font(.subheadline.bold())
            }
            .font(.subheadline)
        }
        .padding(.vertical, 4)
        .onAppear {
            qtyText = item.qty.truncatingRemainder(dividingBy: 1) == 0
                ? String(Int(item.qty)) : String(format: "%.2f", item.qty)
            priceText = String(format: "%.2f", item.unitPrice)
        }
    }
}

#endif
