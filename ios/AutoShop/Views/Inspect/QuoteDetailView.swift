import SwiftUI

#if os(iOS)

struct QuoteDetailView: View {
    let quoteId: String
    var presentedFromChat: Bool = false
    @Environment(\.dismiss) private var dismiss
    @State private var quote: QuoteResponse?
    @State private var editableItems: [EditableLineItem] = []
    @State private var isLoading = true
    @State private var isFinalizing = false
    @State private var isSaving = false
    @State private var editingItem: EditableLineItem?
    @State private var isAddingItem = false
    @State private var addingType = "labor"
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
                    Image(systemName: "doc.text.fill").font(.largeTitle).foregroundStyle(.secondary)
                    Text("Quote not found").font(.headline)
                    Text("ID: \(quoteId.prefix(8))…").font(.caption.monospaced()).foregroundStyle(.tertiary)
                    Button("Retry") { Task { await loadQuote() } }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .navigationTitle("Repair Quote")
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
        let isDraft = q.status == "draft"
        let grandTotal = editableItems.reduce(0.0) { $0 + $1.total }

        ScrollView {
            VStack(spacing: 16) {

                // Line items card
                sectionCard(title: "Line Items") {
                    if editableItems.isEmpty {
                        HStack(spacing: 12) {
                            Image(systemName: "list.bullet.clipboard").foregroundStyle(.secondary)
                            VStack(alignment: .leading, spacing: 2) {
                                Text("No line items yet")
                                    .font(.subheadline).foregroundStyle(.secondary)
                                if isDraft {
                                    Text("Use the buttons below to add labor and parts")
                                        .font(.caption).foregroundStyle(.tertiary)
                                }
                            }
                        }
                        .padding(.vertical, 6)
                    } else {
                        // Header
                        HStack {
                            Text("Item").font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading)
                            Text("Qty").font(.caption).foregroundStyle(.secondary).frame(width: 40, alignment: .trailing)
                            Text("$/unit").font(.caption).foregroundStyle(.secondary).frame(width: 54, alignment: .trailing)
                            Text("Total").font(.caption).foregroundStyle(.secondary).frame(width: 60, alignment: .trailing)
                        }
                        .padding(.bottom, 4)
                        Divider()

                        ForEach(editableItems) { item in
                            Button {
                                guard isDraft else { return }
                                editingItem = item
                            } label: {
                                HStack(alignment: .top) {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(item.description.isEmpty ? "—" : item.description)
                                            .font(.subheadline).fontWeight(.medium)
                                            .foregroundStyle(item.description.isEmpty ? .tertiary : .primary)
                                        Text(item.type.capitalized)
                                            .font(.caption2).foregroundStyle(.tertiary)
                                    }
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    Text(formatQty(item.qty)).font(.caption).frame(width: 40, alignment: .trailing)
                                    Text(String(format: "$%.2f", item.unitPrice)).font(.caption).frame(width: 54, alignment: .trailing)
                                    Text(String(format: "$%.2f", item.total)).font(.subheadline.bold()).frame(width: 60, alignment: .trailing)
                                }
                                .padding(.vertical, 8)
                                .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                            Divider()
                        }

                        // Grand total
                        HStack {
                            Text("Grand Total").font(.subheadline.bold()).frame(maxWidth: .infinity, alignment: .leading)
                            Text(String(format: "$%.2f", isDraft ? grandTotal : q.total))
                                .font(.title3.bold()).foregroundStyle(.blue)
                        }
                        .padding(.top, 6)
                    }
                }

                // Add labor / part (draft only)
                if isDraft {
                    HStack(spacing: 10) {
                        Button {
                            addingType = "labor"
                            isAddingItem = true
                        } label: {
                            Label("Add Labor", systemImage: "wrench.and.screwdriver")
                                .font(.subheadline)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 10)
                                .background(Color(.secondarySystemBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                        }
                        Button {
                            addingType = "part"
                            isAddingItem = true
                        } label: {
                            Label("Add Part", systemImage: "shippingbox")
                                .font(.subheadline)
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 10)
                                .background(Color(.secondarySystemBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                        }
                    }
                    .padding(.horizontal)
                }

                // Action buttons
                VStack(spacing: 10) {
                    if isDraft {
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
                                    Label("Generate PDF", systemImage: "doc.text.fill")
                                        .font(.subheadline.bold())
                                }
                            }
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .background(editableItems.isEmpty ? Color(.systemGray4) : Color.indigo)
                            .foregroundStyle(.white)
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                        .disabled(isFinalizing || editableItems.isEmpty)
                    } else {
                        if let url = URL(string: "\(APIClient.shared.baseURL)/quotes/\(q.quoteId)/pdf") {
                            ShareLink(item: url) {
                                Label("Open Estimate PDF", systemImage: "printer.fill")
                                    .font(.subheadline.bold())
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                                    .background(Color.indigo)
                                    .foregroundStyle(.white)
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                        }
                        if let token = finalizeResult?.shareToken {
                            Button {
                                UIPasteboard.general.string = "\(APIClient.shared.baseURL)/r/\(token)"
                            } label: {
                                Label("Copy Customer Link", systemImage: "link")
                                    .font(.subheadline.bold())
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 14)
                                    .background(Color.blue)
                                    .foregroundStyle(.white)
                                    .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                        }
                    }
                }
                .padding(.horizontal)

                Text("ID: \(q.quoteId.prefix(8))…")
                    .font(.caption2.monospaced()).foregroundStyle(.tertiary)
                    .padding(.bottom, 8)
            }
            .padding(.horizontal)
            .padding(.top, 12)
        }
        .background(Color(.systemGroupedBackground))
        .sheet(item: $editingItem) { item in
            EditLineItemSheet(
                item: item,
                isSaving: isSaving,
                onSave: { updated in Task { await saveEdit(updated) } },
                onRemove: { Task { await removeItem(item) } },
                onCancel: { editingItem = nil }
            )
        }
        .sheet(isPresented: $isAddingItem) {
            AddLineItemSheet(
                defaultType: addingType,
                isSaving: isSaving,
                onAdd: { newItem in Task { await addItem(newItem) } },
                onCancel: { isAddingItem = false }
            )
        }
    }

    // MARK: - sectionCard

    @ViewBuilder
    private func sectionCard<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.caption.uppercaseSmallCaps())
                .foregroundStyle(.secondary)
                .padding(.horizontal, 4)
            VStack(alignment: .leading, spacing: 0) {
                content()
            }
            .padding()
            .background(Color(.systemBackground))
            .clipShape(RoundedRectangle(cornerRadius: 12))
        }
    }

    // MARK: - Data ops

    private func loadQuote() async {
        do {
            let q = try await APIClient.shared.fetchQuote(id: quoteId)
            quote = q
            editableItems = q.lineItems.map { EditableLineItem(from: $0) }
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }

    private func saveEdit(_ updated: EditableLineItem) async {
        isSaving = true
        defer { isSaving = false }
        let items = editableItems.map { $0.id == updated.id ? updated : $0 }
        do {
            let resp = try await APIClient.shared.updateQuoteLineItems(quoteId: quoteId, lineItems: items.map { $0.toLineItem() })
            quote = resp
            editableItems = resp.lineItems.map { EditableLineItem(from: $0) }
            editingItem = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func removeItem(_ item: EditableLineItem) async {
        isSaving = true
        defer { isSaving = false }
        let items = editableItems.filter { $0.id != item.id }
        do {
            let resp = try await APIClient.shared.updateQuoteLineItems(quoteId: quoteId, lineItems: items.map { $0.toLineItem() })
            quote = resp
            editableItems = resp.lineItems.map { EditableLineItem(from: $0) }
            editingItem = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func addItem(_ newItem: EditableLineItem) async {
        isSaving = true
        defer { isSaving = false }
        let items = editableItems + [newItem]
        do {
            let resp = try await APIClient.shared.updateQuoteLineItems(quoteId: quoteId, lineItems: items.map { $0.toLineItem() })
            quote = resp
            editableItems = resp.lineItems.map { EditableLineItem(from: $0) }
            isAddingItem = false
        } catch {
            errorMessage = error.localizedDescription
        }
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

    private func formatQty(_ qty: Double) -> String {
        qty.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(qty)) : String(format: "%.1f", qty)
    }
}

// MARK: - Edit Item Sheet

private struct EditLineItemSheet: View {
    let item: EditableLineItem
    let isSaving: Bool
    let onSave: (EditableLineItem) -> Void
    let onRemove: () -> Void
    let onCancel: () -> Void

    @State private var type: String
    @State private var desc: String
    @State private var qtyText: String
    @State private var priceText: String

    init(item: EditableLineItem, isSaving: Bool, onSave: @escaping (EditableLineItem) -> Void, onRemove: @escaping () -> Void, onCancel: @escaping () -> Void) {
        self.item = item
        self.isSaving = isSaving
        self.onSave = onSave
        self.onRemove = onRemove
        self.onCancel = onCancel
        _type = State(initialValue: item.type)
        _desc = State(initialValue: item.description)
        _qtyText = State(initialValue: item.qty.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(item.qty)) : String(format: "%.2f", item.qty))
        _priceText = State(initialValue: String(format: "%.2f", item.unitPrice))
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Type", selection: $type) {
                        Text("Labor").tag("labor")
                        Text("Part").tag("part")
                    }
                    TextField("Description", text: $desc)
                }
                Section("Pricing") {
                    LabeledContent(type == "labor" ? "Hours" : "Qty") {
                        TextField("1", text: $qtyText)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                    LabeledContent("Unit price ($)") {
                        TextField("0.00", text: $priceText)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                }
                Section {
                    Button("Remove Item", role: .destructive) { onRemove() }
                        .disabled(isSaving)
                }
            }
            .navigationTitle(item.description.isEmpty ? "Edit Item" : item.description)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { onCancel() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        var updated = item
                        updated.type = type
                        updated.description = desc
                        updated.qty = Double(qtyText) ?? item.qty
                        updated.unitPrice = Double(priceText) ?? item.unitPrice
                        onSave(updated)
                    }
                    .disabled(isSaving)
                }
            }
        }
        .presentationDetents([.medium])
    }
}

// MARK: - Add Item Sheet

private struct AddLineItemSheet: View {
    let defaultType: String
    let isSaving: Bool
    let onAdd: (EditableLineItem) -> Void
    let onCancel: () -> Void

    @State private var type: String
    @State private var desc = ""
    @State private var qtyText = "1"
    @State private var priceText = "0.00"

    init(defaultType: String, isSaving: Bool, onAdd: @escaping (EditableLineItem) -> Void, onCancel: @escaping () -> Void) {
        self.defaultType = defaultType
        self.isSaving = isSaving
        self.onAdd = onAdd
        self.onCancel = onCancel
        _type = State(initialValue: defaultType)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Type", selection: $type) {
                        Text("Labor").tag("labor")
                        Text("Part").tag("part")
                    }
                    TextField("Description", text: $desc)
                }
                Section("Pricing") {
                    LabeledContent(type == "labor" ? "Hours" : "Qty") {
                        TextField("1", text: $qtyText)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                    LabeledContent("Unit price ($)") {
                        TextField("0.00", text: $priceText)
                            .keyboardType(.decimalPad)
                            .multilineTextAlignment(.trailing)
                    }
                }
            }
            .navigationTitle("New \(type == "labor" ? "Labor" : "Part")")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { onCancel() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Add") {
                        var newItem = EditableLineItem(type: type)
                        newItem.description = desc
                        newItem.qty = Double(qtyText) ?? 1
                        newItem.unitPrice = Double(priceText) ?? 0
                        onAdd(newItem)
                    }
                    .disabled(isSaving || desc.trimmingCharacters(in: .whitespaces).isEmpty)
                }
            }
        }
        .presentationDetents([.medium])
    }
}

#endif
