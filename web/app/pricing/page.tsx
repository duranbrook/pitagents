import Link from 'next/link'

const plans = [
  {
    badge: 'Basic',
    badgeBg: '#f8fafc',
    badgeColor: '#64748b',
    name: 'Solo Shop',
    desc: 'For a one-person operation. Get AI-generated reports without the admin overhead.',
    price: '$10',
    priceSub: '/month',
    highlight: false,
    features: [
      '1 user account',
      '1 shop location',
      'AI-generated repair reports',
    ],
    cta: 'Get started',
    ctaHref: '/login',
    ctaBg: '#f8fafc',
    ctaColor: '#0f172a',
    ctaBorder: '1.5px solid #e2e8f0',
  },
  {
    badge: 'Starter',
    badgeBg: '#fff7ed',
    badgeColor: '#d97706',
    name: 'Single Shop',
    desc: 'Everything you need to run one location with a full AI crew.',
    price: '$39',
    priceSub: '/month',
    highlight: true,
    features: [
      '1 shop location',
      'Up to 5 staff accounts',
      'AI Technician Assistant',
      'Owner AI Crew',
      'Consumer vehicle history',
    ],
    cta: 'Get started',
    ctaHref: '/login',
    ctaBg: '#d97706',
    ctaColor: '#fff',
    ctaBorder: 'none',
  },
  {
    badge: 'Enterprise',
    badgeBg: '#f8fafc',
    badgeColor: '#64748b',
    name: 'Multi-Location',
    desc: 'Custom pricing for groups, chains, and dealerships.',
    price: "Let's talk",
    priceSub: '',
    highlight: false,
    features: [
      'Multiple shop locations',
      'Unlimited staff accounts',
      'Everything in Starter',
      'Priority support & onboarding',
      'Custom integrations (DMS, fleet)',
    ],
    cta: 'Request a Demo →',
    ctaHref: '/demo',
    ctaBg: '#fff',
    ctaColor: '#0f172a',
    ctaBorder: '1.5px solid #e2e8f0',
  },
]

export default function PricingPage() {
  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif", background: '#f8fafc', minHeight: '100vh', color: '#0f172a' }}>

      {/* NAV */}
      <nav style={{
        background: 'rgba(255,255,255,0.92)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid #f1f5f9',
        padding: '0 64px',
        height: 62,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: 9, fontWeight: 800, fontSize: 15, color: '#0f172a', letterSpacing: -0.3, textDecoration: 'none' }}>
          <div style={{ width: 30, height: 30, background: 'linear-gradient(135deg, #d97706, #b45309)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 14, boxShadow: '0 2px 8px rgba(217,119,6,0.3)' }}>A</div>
          AutoShop
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
          <Link href="/#product" style={{ fontSize: 13.5, color: '#64748b', textDecoration: 'none', fontWeight: 500 }}>Product</Link>
          <Link href="/pricing" style={{ fontSize: 13.5, color: '#0f172a', textDecoration: 'none', fontWeight: 600 }}>Pricing</Link>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/login" style={{ fontSize: 13.5, color: '#64748b', fontWeight: 500, textDecoration: 'none' }}>Sign In</Link>
          <Link href="/demo" style={{
            background: '#d97706', color: '#fff', padding: '8px 18px',
            borderRadius: 8, fontSize: 13.5, fontWeight: 600,
            boxShadow: '0 1px 4px rgba(217,119,6,0.25)', textDecoration: 'none',
          }}>Request Demo</Link>
        </div>
      </nav>

      {/* HEADER */}
      <div style={{ textAlign: 'center', padding: '72px 64px 56px' }}>
        <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, color: '#d97706', textTransform: 'uppercase', marginBottom: 12 }}>Pricing</div>
        <h1 style={{ fontSize: 48, fontWeight: 900, letterSpacing: -1.5, lineHeight: 1.1, marginBottom: 16 }}>Simple, transparent pricing</h1>
        <p style={{ fontSize: 16, color: '#64748b', lineHeight: 1.65, maxWidth: 440, margin: '0 auto' }}>
          Start at $10/month. Scale as your shop grows.
        </p>
      </div>

      {/* PLANS GRID */}
      <div style={{ maxWidth: 1040, margin: '0 auto', padding: '0 40px 96px', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20, alignItems: 'start' }}>
        {plans.map(plan => (
          <div
            key={plan.badge}
            style={{
              background: '#fff',
              border: plan.highlight ? '2px solid #d97706' : '1px solid #e2e8f0',
              borderRadius: 20,
              padding: 36,
              boxShadow: plan.highlight ? '0 4px 24px rgba(217,119,6,0.1)' : 'none',
              position: 'relative',
            }}
          >
            {plan.highlight && (
              <div style={{
                position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)',
                background: '#d97706', color: '#fff', fontSize: 10, fontWeight: 700,
                padding: '3px 14px', borderRadius: 99, letterSpacing: 1, textTransform: 'uppercase',
                whiteSpace: 'nowrap',
              }}>Most popular</div>
            )}
            <div style={{ display: 'inline-block', background: plan.badgeBg, color: plan.badgeColor, fontSize: 10, fontWeight: 700, padding: '4px 12px', borderRadius: 99, marginBottom: 20, letterSpacing: 1, textTransform: 'uppercase' }}>{plan.badge}</div>
            <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>{plan.name}</div>
            <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 28, lineHeight: 1.5 }}>{plan.desc}</p>
            <div style={{ fontSize: plan.price.startsWith('$') ? 52 : 28, fontWeight: 900, color: plan.highlight ? '#d97706' : '#0f172a', letterSpacing: -1, lineHeight: 1, marginBottom: 4 }}>
              {plan.price.startsWith('$') && <sup style={{ fontSize: 24, letterSpacing: 0, verticalAlign: 'super' }}>$</sup>}
              {plan.price.startsWith('$') ? plan.price.slice(1) : plan.price}
              {plan.priceSub && <sub style={{ fontSize: 14, fontWeight: 400, color: '#94a3b8', letterSpacing: 0, verticalAlign: 'baseline' }}>{plan.priceSub}</sub>}
            </div>
            <hr style={{ border: 'none', borderTop: '1px solid #f1f5f9', margin: '24px 0' }} />
            {plan.features.map(f => (
              <div key={f} style={{ fontSize: 13, color: '#475569', padding: '6px 0', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                <span style={{ color: '#d97706', fontWeight: 700, flexShrink: 0 }}>✓</span> {f}
              </div>
            ))}
            <Link href={plan.ctaHref} style={{
              display: 'block', width: '100%', marginTop: 32, padding: '13px',
              borderRadius: 10, fontSize: 14, fontWeight: 700, textAlign: 'center',
              background: plan.ctaBg, color: plan.ctaColor,
              border: plan.ctaBorder,
              boxShadow: plan.highlight ? '0 2px 8px rgba(217,119,6,0.3)' : 'none',
              textDecoration: 'none',
            }}>{plan.cta}</Link>
          </div>
        ))}
      </div>

      {/* FAQ ROW */}
      <div style={{ background: '#fff', borderTop: '1px solid #e2e8f0', padding: '56px 64px' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 40 }}>
          {[
            { q: 'Can I upgrade later?', a: 'Yes. Move between plans at any time. Changes take effect at the next billing cycle.' },
            { q: 'Is there a free trial?', a: 'Request a demo and we\'ll set you up with a guided walkthrough before you commit.' },
            { q: 'What counts as a user?', a: 'Any staff account that logs into AutoShop — technicians, service advisors, or the owner.' },
            { q: 'Do consumers pay anything?', a: 'No. Vehicle history access is free for car owners. The shop pays the subscription.' },
          ].map(item => (
            <div key={item.q}>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', marginBottom: 6 }}>{item.q}</div>
              <div style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>{item.a}</div>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}
