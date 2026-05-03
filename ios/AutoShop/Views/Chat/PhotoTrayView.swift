import SwiftUI

struct PhotoTrayView: View {
    @Binding var photos: [AttachedPhoto]
    var onAddMore: (() -> Void)? = nil

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(photos.indices, id: \.self) { i in
                    photoThumb(index: i)
                }
                addMoreButton
            }
        }
    }

    private func photoThumb(index: Int) -> some View {
        let photo = photos[index]
        return ZStack(alignment: .topTrailing) {
            Image(uiImage: photo.image)
                .resizable()
                .scaledToFill()
                .frame(width: 60, height: 60)
                .clipped()
                .clipShape(RoundedRectangle(cornerRadius: 10))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .strokeBorder(
                            photo.isVIN ? Color.orange : (photo.isSelected ? Color.accentColor : Color.clear),
                            lineWidth: 2.5
                        )
                )
                .overlay(alignment: .bottomTrailing) {
                    if photo.isVideo {
                        Image(systemName: "play.circle.fill")
                            .font(.system(size: 22))
                            .foregroundStyle(.white.shadow(.drop(radius: 1)))
                            .padding(4)
                    } else if photo.isVIN {
                        Text("VIN")
                            .font(.system(size: 9, weight: .black))
                            .foregroundStyle(.white)
                            .padding(.horizontal, 4)
                            .padding(.vertical, 2)
                            .background(Color.orange)
                            .clipShape(RoundedRectangle(cornerRadius: 4))
                            .padding(3)
                    } else if photo.isSelected {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 16))
                            .foregroundStyle(.white, Color.accentColor)
                            .padding(3)
                    }
                }
                .onTapGesture { photos[index].isSelected.toggle() }
                .contextMenu {
                    Button {
                        photos[index].isVIN = true
                        for j in photos.indices where j != index { photos[j].isVIN = false }
                    } label: { Label("Mark as VIN photo", systemImage: "barcode.viewfinder") }

                    Button(role: .destructive) {
                        photos.remove(at: index)
                    } label: { Label("Remove", systemImage: "trash") }
                }

            // Delete badge — top-right corner
            Button {
                photos.remove(at: index)
            } label: {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 18))
                    .foregroundStyle(.white, Color(.systemGray))
                    .background(Color(.systemBackground).clipShape(Circle()))
            }
            .offset(x: 6, y: -6)
        }
    }

    private var addMoreButton: some View {
        Button { onAddMore?() } label: {
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(Color(.separator), lineWidth: 1.5)
                .frame(width: 60, height: 60)
                .overlay(Image(systemName: "plus").foregroundStyle(.secondary))
        }
    }
}
