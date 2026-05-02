// web/components/home/HomePage.tsx
'use client'

import Link from 'next/link'

export function HomePage() {
  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif", background: '#fff', color: '#0f172a' }}>

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
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, fontWeight: 800, fontSize: 15, color: '#0f172a', letterSpacing: -0.3 }}>
          <div style={{ width: 30, height: 30, background: 'linear-gradient(135deg, #2563eb, #1d4ed8)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 14, boxShadow: '0 2px 8px rgba(37,99,235,0.3)' }}>A</div>
          AutoShop
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
          <a href="#product" style={{ fontSize: 13.5, color: '#64748b', textDecoration: 'none', fontWeight: 500 }}>Product</a>
          <a href="#pricing" style={{ fontSize: 13.5, color: '#64748b', textDecoration: 'none', fontWeight: 500 }}>Pricing</a>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/login" style={{ fontSize: 13.5, color: '#64748b', fontWeight: 500, textDecoration: 'none' }}>Sign In</Link>
          <Link href="/demo" style={{
            background: '#2563eb', color: '#fff', padding: '8px 18px',
            borderRadius: 8, fontSize: 13.5, fontWeight: 600,
            boxShadow: '0 1px 4px rgba(37,99,235,0.25)', textDecoration: 'none',
          }}>Request Demo</Link>
        </div>
      </nav>

      {/* HERO */}
      <section style={{
        background: 'linear-gradient(160deg, #f0f7ff 0%, #ffffff 50%, #f8faff 100%)',
        padding: '100px 64px 80px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', top: -120, left: '50%', transform: 'translateX(-50%)',
          width: 700, height: 700,
          background: 'radial-gradient(circle, rgba(37,99,235,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          background: '#fff', border: '1px solid #e2e8f0',
          color: '#475569', fontSize: 12, fontWeight: 600,
          padding: '5px 14px', borderRadius: 99, marginBottom: 28,
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        }}>
          <span style={{ width: 6, height: 6, background: '#22c55e', borderRadius: '50%', display: 'inline-block' }} />
          Now live for independent auto shops
        </div>

        <h1 style={{ fontSize: 58, fontWeight: 900, lineHeight: 1.08, color: '#0f172a', maxWidth: 720, margin: '0 auto 22px', letterSpacing: -2 }}>
          Give your shop{' '}
          <em style={{
            fontStyle: 'normal',
            background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>AI superpowers</em>
        </h1>
        <p style={{ fontSize: 18, color: '#64748b', maxWidth: 520, margin: '0 auto 40px', lineHeight: 1.65 }}>
          Automate inspections, empower technicians, and keep every customer connected — across every shop they visit.
        </p>

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', alignItems: 'center', marginBottom: 60 }}>
          <Link href="/demo" style={{
            background: '#2563eb', color: '#fff', padding: '13px 28px',
            borderRadius: 9, fontSize: 15, fontWeight: 700,
            boxShadow: '0 4px 14px rgba(37,99,235,0.35)', textDecoration: 'none',
          }}>Request a Demo</Link>
          <Link href="/login" style={{
            color: '#475569', fontSize: 15, fontWeight: 500,
            background: 'none', border: '1.5px solid #e2e8f0',
            borderRadius: 9, padding: '12px 22px', textDecoration: 'none',
          }}>Sign in →</Link>
        </div>

        <div style={{
          maxWidth: 860, margin: '0 auto',
          background: '#fff', border: '1px solid #e2e8f0',
          borderRadius: 14, overflow: 'hidden',
          boxShadow: '0 20px 60px rgba(0,0,0,0.10), 0 4px 16px rgba(0,0,0,0.06)',
        }}>
          <div style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#f87171', display: 'inline-block' }} />
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#fbbf24', display: 'inline-block' }} />
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#4ade80', display: 'inline-block' }} />
            <div style={{ flex: 1, background: '#f1f5f9', borderRadius: 4, height: 14, marginLeft: 10 }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', minHeight: 260 }}>
            <div style={{ background: '#0f172a', padding: '20px 16px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)', letterSpacing: 1, padding: '0 10px 12px' }}>AUTOSHOP</div>
              {[
                { label: 'Dashboard', active: true },
                { label: 'Chat', active: false },
                { label: 'Inspections', active: false },
                { label: 'Job Cards', active: false },
                { label: 'Customers', active: false },
                { label: 'Reports', active: false },
              ].map(item => (
                <div key={item.label} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '7px 10px', borderRadius: 7, fontSize: 11,
                  color: item.active ? '#fff' : 'rgba(255,255,255,0.5)',
                  background: item.active ? 'rgba(255,255,255,0.08)' : 'transparent',
                  fontWeight: item.active ? 600 : 400,
                  marginBottom: 2,
                }}>
                  <div style={{ width: 14, height: 14, borderRadius: 3, background: item.active ? '#2563eb' : 'rgba(255,255,255,0.15)' }} />
                  {item.label}
                </div>
              ))}
            </div>
            <div style={{ padding: '20px 24px' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#0f172a', marginBottom: 14 }}>Good morning, Marcus 👋</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
                {[
                  { val: '12', label: 'Open Jobs' },
                  { val: '$8.4k', label: 'Revenue today' },
                  { val: '94%', label: 'Satisfaction' },
                ].map(stat => (
                  <div key={stat.label} style={{ background: '#f8fafc', border: '1px solid #f1f5f9', borderRadius: 8, padding: '10px 12px' }}>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 2 }}>{stat.val}</div>
                    <div style={{ fontSize: 9, color: '#94a3b8', fontWeight: 500 }}>{stat.label}</div>
                  </div>
                ))}
              </div>
              <div style={{ background: '#f8fafc', borderRadius: 8, padding: '12px 14px', border: '1px solid #f1f5f9' }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: '#64748b', marginBottom: 8 }}>Ask your AI →</div>
                <div style={{ fontSize: 10, color: '#475569', padding: '6px 10px', background: '#fff', borderRadius: 6, border: '1px solid #f1f5f9', marginBottom: 6 }}>What&apos;s our top repair this week?</div>
                <div style={{ fontSize: 10, color: '#fff', padding: '6px 10px', background: '#2563eb', borderRadius: 6, display: 'inline-block' }}>Brake service — 7 jobs, $3,220 revenue. Up 18% vs last week.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* METRICS BAND */}
      <div style={{ background: '#0f172a', padding: '40px 64px', display: 'flex', justifyContent: 'center', gap: 80 }}>
        {[
          { val: '2×', label: 'Faster inspections' },
          { val: '40% less admin', label: 'Per technician daily' },
          { val: '100%', label: 'Repair history coverage' },
          { val: '$0', label: 'For your customers' },
        ].map(m => (
          <div key={m.label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 36, fontWeight: 900, color: '#60a5fa', letterSpacing: -1 }}>{m.val}</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 4, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1 }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* PRODUCT SECTION */}
      <section id="product" style={{ padding: '96px 64px', background: '#fff' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: '#2563eb', textTransform: 'uppercase', marginBottom: 12 }}>Product</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.1, marginBottom: 14 }}>Built for every role<br />in your shop</h2>
          <p style={{ fontSize: 16, color: '#64748b', maxWidth: 480, lineHeight: 1.65, marginBottom: 56 }}>From the owner&apos;s chair to the technician&apos;s bay — everyone gets the right AI at the right moment.</p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff' }}>
              <div style={{ padding: '24px 24px 0', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 150 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
                  {[{ n: '$24k', l: 'Monthly Rev' }, { n: '47', l: 'Jobs Done' }, { n: '98%', l: 'Satisfaction' }].map(s => (
                    <div key={s.l} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 10 }}>
                      <div style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>{s.n}</div>
                      <div style={{ fontSize: 9, color: '#94a3b8' }}>{s.l}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>📊</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>Owner Intelligence</div>
                </div>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>Ask any question about your shop — revenue, team performance, job status — and get instant answers. AI agents with full visibility across every department.</p>
              </div>
            </div>

            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff' }}>
              <div style={{ padding: '24px 24px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 150 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ fontSize: 10, padding: '7px 10px', borderRadius: 8, background: '#eff6ff', color: '#1d4ed8', alignSelf: 'flex-end', maxWidth: '90%' }}>Customer says the brakes squeal at low speed.</div>
                  <div style={{ fontSize: 10, padding: '7px 10px', borderRadius: 8, background: '#fff', border: '1px solid #e2e8f0', color: '#0f172a', maxWidth: '90%' }}>Likely glazed pads or worn rotors. Check pad thickness — if under 3mm, recommend replacement. I&apos;ll draft the repair note.</div>
                </div>
              </div>
              <div style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>🔧</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>AI Technician Assistant</div>
                </div>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>Every technician gets a dedicated AI co-pilot. It guides inspections, drafts repair notes, looks up parts, and handles the paperwork — so they can stay under the hood.</p>
              </div>
            </div>

            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff' }}>
              <div style={{ padding: '16px 24px 0', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 150 }}>
                {[
                  { shop: 'City Auto Center', repair: 'Brake pad replacement + rotor resurface', date: 'Mar 2026' },
                  { shop: 'QuickLube Express', repair: 'Oil change + tire rotation', date: 'Jan 2026' },
                  { shop: 'Downtown Motors', repair: 'AC recharge + cabin filter', date: 'Nov 2025' },
                ].map(r => (
                  <div key={r.shop} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 7, padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 600, color: '#0f172a' }}>{r.shop}</div>
                      <div style={{ fontSize: 9, color: '#64748b', marginTop: 1 }}>{r.repair}</div>
                    </div>
                    <div style={{ fontSize: 9, color: '#94a3b8' }}>{r.date}</div>
                  </div>
                ))}
              </div>
              <div style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: '#fdf4ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>🚗</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>Consumer Vehicle History</div>
                </div>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>Customers see their complete repair history across every shop they&apos;ve ever visited. One timeline. Every vehicle. Every repair — no more lost records.</p>
              </div>
            </div>

            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff' }}>
              <div style={{ padding: '32px 24px 0', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 150, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 8, alignItems: 'center', textAlign: 'center', width: '100%' }}>
                  <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: 8, fontSize: 9, fontWeight: 600, color: '#1d4ed8' }}>Shop Owner</div>
                  <div style={{ fontSize: 14, color: '#cbd5e1' }}>⇄</div>
                  <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: 8, fontSize: 9, fontWeight: 600, color: '#1d4ed8' }}>Technician</div>
                  <div style={{ gridColumn: '1/-1', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginTop: 4 }}>
                    <span style={{ fontSize: 9, color: '#94a3b8' }}>connected via</span>
                    <span style={{ fontSize: 10, fontWeight: 700, color: '#2563eb' }}>AutoShop Platform</span>
                  </div>
                  <div style={{ gridColumn: '2', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 8, fontSize: 9, fontWeight: 600, color: '#475569' }}>Consumer</div>
                </div>
              </div>
              <div style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: '#fff7ed', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>🔗</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>Connected Ecosystem</div>
                </div>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>Shops, technicians, and customers all on one platform. Records, updates, and repair history flow seamlessly between every party in the repair lifecycle.</p>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* WHY SECTION */}
      <section style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', padding: '96px 64px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: '#60a5fa', textTransform: 'uppercase', marginBottom: 12 }}>Why AutoShop</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#f8fafc', letterSpacing: -1, lineHeight: 1.1, marginBottom: 12 }}>AI that works for the<br />whole automotive world</h2>
          <p style={{ fontSize: 16, color: 'rgba(255,255,255,0.45)', maxWidth: 480, lineHeight: 1.65, marginBottom: 48 }}>Two transformations. One platform.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {[
              { num: '01', title: 'Superpower every shop', body: 'AutoShop brings enterprise-grade AI to independent auto shops. Automate quotes, inspections, scheduling, and reporting — without adding headcount.' },
              { num: '02', title: 'Connect every consumer', body: "For the first time, customers can access their complete repair history across every shop they've used. One timeline. Every vehicle. Every repair." },
            ].map(card => (
              <div key={card.num} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 16, padding: 36 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#3b82f6', letterSpacing: 2, marginBottom: 16 }}>{card.num}</div>
                <h3 style={{ fontSize: 22, fontWeight: 800, color: '#f1f5f9', marginBottom: 12, letterSpacing: -0.3 }}>{card.title}</h3>
                <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', lineHeight: 1.75 }}>{card.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TESTIMONIAL */}
      <section style={{ background: '#f8fafc', padding: '80px 64px' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', textAlign: 'center' }}>
          <div style={{ fontSize: 64, lineHeight: 1, color: '#e2e8f0', fontFamily: 'Georgia, serif', marginBottom: -10 }}>&ldquo;</div>
          <p style={{ fontSize: 22, fontWeight: 600, color: '#0f172a', lineHeight: 1.55, letterSpacing: -0.3, marginBottom: 28 }}>
            AutoShop cut our inspection write-up time in half. My technicians actually enjoy using it — and customers love seeing their full vehicle history in one place.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg,#2563eb,#7c3aed)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 14 }}>M</div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>Marcus T.</div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>Owner, City Auto Center</div>
            </div>
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" style={{ padding: '96px 64px', background: '#fff' }}>
        <div style={{ maxWidth: 980, margin: '0 auto' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: '#2563eb', textTransform: 'uppercase', marginBottom: 12 }}>Pricing</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.1, marginBottom: 14 }}>Simple, transparent pricing</h2>
          <p style={{ fontSize: 16, color: '#64748b', lineHeight: 1.65 }}>Start at $39/month. Scale when you&apos;re ready.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 56 }}>

            <div style={{ border: '2px solid #2563eb', borderRadius: 20, padding: 36, boxShadow: '0 4px 24px rgba(37,99,235,0.1)' }}>
              <div style={{ display: 'inline-block', background: '#eff6ff', color: '#2563eb', fontSize: 10, fontWeight: 700, padding: '4px 12px', borderRadius: 99, marginBottom: 20, letterSpacing: 1, textTransform: 'uppercase' as const }}>Starter</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>Single Shop</div>
              <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 28, lineHeight: 1.5 }}>Everything you need to run one location with AI.</p>
              <div style={{ fontSize: 52, fontWeight: 900, color: '#0f172a', letterSpacing: -2, lineHeight: 1, marginBottom: 4 }}>
                <sup style={{ fontSize: 24, letterSpacing: 0, verticalAlign: 'super' }}>$</sup>39<sub style={{ fontSize: 14, fontWeight: 400, color: '#94a3b8', letterSpacing: 0, verticalAlign: 'baseline' }}>/month</sub>
              </div>
              <hr style={{ border: 'none', borderTop: '1px solid #f1f5f9', margin: '24px 0' }} />
              {['1 shop location', 'Up to 5 staff accounts', 'AI Technician Assistant', 'Owner Intelligence Dashboard', 'Consumer vehicle history'].map(f => (
                <div key={f} style={{ fontSize: 13, color: '#475569', padding: '6px 0', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ color: '#2563eb', fontWeight: 700, flexShrink: 0 }}>✓</span> {f}
                </div>
              ))}
              <Link href="/login" style={{
                display: 'block', width: '100%', marginTop: 32, padding: '13px',
                borderRadius: 10, fontSize: 14, fontWeight: 700, textAlign: 'center',
                background: '#2563eb', color: '#fff',
                boxShadow: '0 2px 8px rgba(37,99,235,0.3)', textDecoration: 'none',
              }}>Get started</Link>
            </div>

            <div style={{ border: '1px solid #e2e8f0', borderRadius: 20, padding: 36 }}>
              <div style={{ display: 'inline-block', background: '#f8fafc', color: '#64748b', fontSize: 10, fontWeight: 700, padding: '4px 12px', borderRadius: 99, marginBottom: 20, letterSpacing: 1, textTransform: 'uppercase' as const }}>Enterprise</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>Multi-Location</div>
              <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 28, lineHeight: 1.5 }}>Custom pricing for groups, chains, and dealerships.</p>
              <div style={{ fontSize: 32, fontWeight: 900, color: '#2563eb', letterSpacing: -0.5, lineHeight: 1, marginBottom: 4 }}>Let&apos;s talk</div>
              <hr style={{ border: 'none', borderTop: '1px solid #f1f5f9', margin: '24px 0' }} />
              {['Multiple shop locations', 'Unlimited staff accounts', 'Everything in Starter', 'Priority support & onboarding', 'Custom integrations (DMS, fleet)'].map(f => (
                <div key={f} style={{ fontSize: 13, color: '#475569', padding: '6px 0', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ color: '#2563eb', fontWeight: 700, flexShrink: 0 }}>✓</span> {f}
                </div>
              ))}
              <Link href="/demo" style={{
                display: 'block', width: '100%', marginTop: 32, padding: '13px',
                borderRadius: 10, fontSize: 14, fontWeight: 700, textAlign: 'center',
                background: '#fff', color: '#0f172a',
                border: '1.5px solid #e2e8f0', textDecoration: 'none',
              }}>Request a Demo →</Link>
            </div>

          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ background: '#0f172a', padding: '40px 64px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 14, color: '#fff' }}>
          <div style={{ width: 24, height: 24, background: 'linear-gradient(135deg,#2563eb,#1d4ed8)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 11 }}>A</div>
          AutoShop
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          {['Privacy', 'Terms', 'Contact'].map(l => (
            <a key={l} href="#" style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', textDecoration: 'none' }}>{l}</a>
          ))}
        </div>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>© 2026 AutoShop. All rights reserved.</div>
      </footer>

    </div>
  )
}
