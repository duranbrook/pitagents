export function AppBackground() {
  return (
    <div className="fixed inset-0" style={{ zIndex: -1 }}>
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: "url('/garage-bg.jpg')",
          backgroundSize: 'cover',
          backgroundPosition: 'center 40%',
        }}
      />
      {/* Overlay opacity is controlled by the --bg-overlay CSS variable.
          CSS variables are live — changing the var via useTheme() updates
          this div's background instantly without a React re-render. */}
      <div
        className="absolute inset-0"
        style={{
          background: 'var(--bg-overlay)',
          transition: 'background 0.3s ease',
        }}
      />
    </div>
  )
}
