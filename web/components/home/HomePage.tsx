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
          <div style={{ width: 30, height: 30, background: 'linear-gradient(135deg, #d97706, #b45309)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 14, boxShadow: '0 2px 8px rgba(217,119,6,0.3)' }}>A</div>
          AutoShop
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
          <a href="#product" style={{ fontSize: 13.5, color: '#64748b', textDecoration: 'none', fontWeight: 500 }}>Product</a>
          <a href="#pricing" style={{ fontSize: 13.5, color: '#64748b', textDecoration: 'none', fontWeight: 500 }}>Pricing</a>
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
          background: 'radial-gradient(circle, rgba(217,119,6,0.08) 0%, transparent 70%)',
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
            background: 'linear-gradient(135deg, #d97706, #f59e0b)',
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
            background: '#d97706', color: '#fff', padding: '13px 28px',
            borderRadius: 9, fontSize: 15, fontWeight: 700,
            boxShadow: '0 4px 14px rgba(217,119,6,0.35)', textDecoration: 'none',
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
                  <div style={{ width: 14, height: 14, borderRadius: 3, background: item.active ? '#d97706' : 'rgba(255,255,255,0.15)' }} />
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
                <div style={{ fontSize: 10, color: '#fff', padding: '6px 10px', background: '#d97706', borderRadius: 6, display: 'inline-block' }}>Brake service — 7 jobs, $3,220 revenue. Up 18% vs last week.</div>
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
            <div style={{ fontSize: 36, fontWeight: 900, color: '#fb923c', letterSpacing: -1 }}>{m.val}</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 4, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1 }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* PROBLEM SECTION */}
      <section id="product" style={{ padding: '80px 64px', background: '#fff', borderBottom: '1px solid #e2e8f0' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, color: '#dc2626', textTransform: 'uppercase', marginBottom: 12 }}>The Problem</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.15, marginBottom: 14 }}>
            Auto shops run on skill.<br />They shouldn&apos;t run on software juggling.
          </h2>
          <p style={{ fontSize: 15, color: '#64748b', maxWidth: 560, lineHeight: 1.65, marginBottom: 52 }}>
            Every day, technicians, owners, and car owners lose time and records to tools that weren&apos;t built for them — or weren&apos;t built to work together.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>

            {/* Technician */}
            <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: '#d97706', marginBottom: 14 }}>🔧 The Technician</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  'After every job: 20+ minutes of manual write-ups, repair notes, and part lookups',
                  'Estimates built by hand — every time, from scratch',
                  'Time spent on paperwork is time not spent on cars',
                ].map(point => (
                  <li key={point} style={{ fontSize: 13, color: '#374151', lineHeight: 1.55, display: 'flex', gap: 10 }}>
                    <span style={{ color: '#cbd5e1', flexShrink: 0 }}>—</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Owner */}
            <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: '#2563eb', marginBottom: 14 }}>👥 The Shop Owner</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  'Running the shop means managing multiple disconnected tools — scheduling, invoicing, parts, payroll',
                  'Every new tool has a learning curve — and you still have to stitch the answers together yourself',
                  'Switching tools means retraining the whole team',
                ].map(point => (
                  <li key={point} style={{ fontSize: 13, color: '#374151', lineHeight: 1.55, display: 'flex', gap: 10 }}>
                    <span style={{ color: '#cbd5e1', flexShrink: 0 }}>—</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Car owner */}
            <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 24 }}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: 1.5, textTransform: 'uppercase' as const, color: '#16a34a', marginBottom: 14 }}>🚗 The Car Owner</div>
              <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  'Every time you switch shops, your history starts over — the new shop knows nothing',
                  "Buy a used car? You have no idea what the previous owner actually maintained — or skipped",
                  "Even as the current owner, it's easy to forget what's been done and when",
                  'When you sell the car, all your maintenance records disappear with it',
                ].map(point => (
                  <li key={point} style={{ fontSize: 13, color: '#374151', lineHeight: 1.55, display: 'flex', gap: 10 }}>
                    <span style={{ color: '#cbd5e1', flexShrink: 0 }}>—</span>
                    <span>{point}</span>
                  </li>
                ))}
              </ul>
            </div>

          </div>
        </div>
      </section>

      {/* CONNECTOR */}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px 0', background: '#f8fafc' }}>
        <div style={{ width: 34, height: 34, borderRadius: '50%', background: '#d97706', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: 16, fontWeight: 700 }}>↓</div>
      </div>

      {/* SOLUTION SECTION */}
      <section style={{ padding: '80px 64px', background: '#f8fafc' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 2, color: '#d97706', textTransform: 'uppercase', marginBottom: 12 }}>The Solution</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.15, marginBottom: 14 }}>
            One tool. Three problems solved.
          </h2>
          <p style={{ fontSize: 15, color: '#64748b', maxWidth: 560, lineHeight: 1.65, marginBottom: 52 }}>
            PitAgents puts an AI on every role — technician, shop owner, and car owner — each one built for exactly the job they need to do.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>

            {/* Pillar 1 — AI Technician */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '10px 16px', fontSize: 11, fontWeight: 600, lineHeight: 1.5, background: '#fff7ed', color: '#92400e', borderBottom: '1px solid #fed7aa' }}>
                Handles the write-ups so your technician can stay on the car.
              </div>
              <div style={{ padding: '14px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 160, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 6 }}>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff7ed', color: '#92400e', alignSelf: 'flex-end', maxWidth: '92%', lineHeight: 1.45 }}>Brakes squeal at low speed — 2021 Camry</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #fed7aa', color: '#0f172a', maxWidth: '92%', lineHeight: 1.45 }}>Likely glazed pads. Under 3mm → recommend replacement. Drafting repair note now.</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff7ed', color: '#92400e', alignSelf: 'flex-end', maxWidth: '92%', lineHeight: 1.45 }}>Add a rotor inspection line</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #fed7aa', color: '#0f172a', maxWidth: '92%', lineHeight: 1.45 }}>Done. Ready to send to the customer.</div>
              </div>
              <div style={{ padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: '#fff7ed', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>🔧</div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: '#0f172a' }}>AI Technician Assistant</div>
                </div>
                <p style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>Guides inspections, drafts repair notes, looks up parts, handles paperwork — so techs stay under the hood, not behind a desk.</p>
              </div>
            </div>

            {/* Pillar 2 — Owner AI Crew */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '10px 16px', fontSize: 11, fontWeight: 600, lineHeight: 1.5, background: '#eff6ff', color: '#1e3a5f', borderBottom: '1px solid #bfdbfe' }}>
                Replace the tool stack with one conversation.
              </div>
              <div style={{ padding: '14px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 160, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 6 }}>
                <div style={{ display: 'flex', gap: 5, marginBottom: 2 }}>
                  {['Service Advisor', 'Bookkeeper', 'Manager'].map(name => (
                    <span key={name} style={{
                      fontSize: 8, fontWeight: 700, padding: '3px 8px', borderRadius: 99,
                      ...(name === 'Bookkeeper'
                        ? { background: '#1d4ed8', color: '#fff' }
                        : { background: '#f1f5f9', color: '#64748b', border: '1px solid #e2e8f0' }),
                    }}>{name}</span>
                  ))}
                </div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#eff6ff', color: '#1d4ed8', alignSelf: 'flex-end', maxWidth: '92%', lineHeight: 1.45 }}>Revenue this week vs last?</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #bfdbfe', color: '#0f172a', maxWidth: '92%', lineHeight: 1.45 }}>$18,400 across 34 jobs — up 22% vs last week&apos;s $15,080. Brake jobs drove most of the gain.</div>
              </div>
              <div style={{ padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>👥</div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: '#0f172a' }}>Owner AI Crew</div>
                </div>
                <p style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>A crew of specialists for service, books, and ops. Ask any question in plain language. Dashboard still available when you want it.</p>
              </div>
            </div>

            {/* Pillar 3 — Vehicle History */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff', display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '10px 16px', fontSize: 11, fontWeight: 600, lineHeight: 1.5, background: '#f0fdf4', color: '#14532d', borderBottom: '1px solid #bbf7d0' }}>
                The car&apos;s full history — current owner, previous owners, every shop.
              </div>
              <div style={{ padding: '14px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 160, display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', gap: 6 }}>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#f0fdf4', color: '#166534', alignSelf: 'flex-end', maxWidth: '92%', lineHeight: 1.45 }}>What&apos;s been done on my Civic — including before I bought it?</div>
                <div style={{ fontSize: 10, padding: '6px 10px', borderRadius: 8, background: '#fff', border: '1px solid #bbf7d0', color: '#0f172a', maxWidth: '92%', lineHeight: 1.45 }}>Full history across all owners and 3 shops:</div>
                {[
                  { label: 'City Auto — Brake replacement', date: 'Mar 2026', price: '$480', muted: false },
                  { label: 'Previous owner — Oil change', date: 'Jun 2024', price: '$65', muted: true },
                ].map(row => (
                  <div key={row.label} style={{ fontSize: 9, padding: '5px 8px', borderRadius: 6, background: '#fff', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 600, color: row.muted ? '#94a3b8' : '#0f172a' }}>{row.label}</span>
                    <span style={{ display: 'flex', gap: 6 }}>
                      <span style={{ color: '#94a3b8' }}>{row.date}</span>
                      <span style={{ color: '#166534', fontWeight: 700 }}>{row.price}</span>
                    </span>
                  </div>
                ))}
                <div style={{ fontSize: 8, color: '#94a3b8', padding: '2px 4px' }}>🔒 Your view only — shops cannot see each other&apos;s records</div>
              </div>
              <div style={{ padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, flexShrink: 0 }}>🚗</div>
                  <div style={{ fontSize: 13, fontWeight: 800, color: '#0f172a' }}>Your Vehicle History</div>
                </div>
                <p style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>Every repair, every price, current and previous owners — all in one place. Follows the car forever. Know exactly what&apos;s been done, and what hasn&apos;t.</p>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* WHY SECTION */}
      <section style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', padding: '96px 64px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: '#fb923c', textTransform: 'uppercase', marginBottom: 12 }}>Why AutoShop</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#f8fafc', letterSpacing: -1, lineHeight: 1.1, marginBottom: 12 }}>AI that works for the<br />whole automotive world</h2>
          <p style={{ fontSize: 16, color: 'rgba(255,255,255,0.45)', maxWidth: 480, lineHeight: 1.65, marginBottom: 48 }}>Two transformations. One platform.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {[
              { num: '01', title: 'Superpower every shop', body: 'AutoShop brings enterprise-grade AI to independent auto shops. Automate quotes, inspections, scheduling, and reporting — without adding headcount.' },
              { num: '02', title: 'Connect every consumer', body: "For the first time, customers can access their complete repair history across every shop they've used. One timeline. Every vehicle. Every repair." },
            ].map(card => (
              <div key={card.num} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 16, padding: 36 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#f59e0b', letterSpacing: 2, marginBottom: 16 }}>{card.num}</div>
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
            <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg,#d97706,#f59e0b)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 14 }}>M</div>
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
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: '#d97706', textTransform: 'uppercase', marginBottom: 12 }}>Pricing</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.1, marginBottom: 14 }}>Simple, transparent pricing</h2>
          <p style={{ fontSize: 16, color: '#64748b', lineHeight: 1.65 }}>Start at $39/month. Scale when you&apos;re ready.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 56 }}>

            <div style={{ border: '2px solid #d97706', borderRadius: 20, padding: 36, boxShadow: '0 4px 24px rgba(217,119,6,0.1)' }}>
              <div style={{ display: 'inline-block', background: '#fff7ed', color: '#d97706', fontSize: 10, fontWeight: 700, padding: '4px 12px', borderRadius: 99, marginBottom: 20, letterSpacing: 1, textTransform: 'uppercase' as const }}>Starter</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>Single Shop</div>
              <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 28, lineHeight: 1.5 }}>Everything you need to run one location with AI.</p>
              <div style={{ fontSize: 52, fontWeight: 900, color: '#0f172a', letterSpacing: -2, lineHeight: 1, marginBottom: 4 }}>
                <sup style={{ fontSize: 24, letterSpacing: 0, verticalAlign: 'super' }}>$</sup>39<sub style={{ fontSize: 14, fontWeight: 400, color: '#94a3b8', letterSpacing: 0, verticalAlign: 'baseline' }}>/month</sub>
              </div>
              <hr style={{ border: 'none', borderTop: '1px solid #f1f5f9', margin: '24px 0' }} />
              {['1 shop location', 'Up to 5 staff accounts', 'AI Technician Assistant', 'Owner Intelligence Dashboard', 'Consumer vehicle history'].map(f => (
                <div key={f} style={{ fontSize: 13, color: '#475569', padding: '6px 0', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ color: '#d97706', fontWeight: 700, flexShrink: 0 }}>✓</span> {f}
                </div>
              ))}
              <Link href="/login" style={{
                display: 'block', width: '100%', marginTop: 32, padding: '13px',
                borderRadius: 10, fontSize: 14, fontWeight: 700, textAlign: 'center',
                background: '#d97706', color: '#fff',
                boxShadow: '0 2px 8px rgba(217,119,6,0.3)', textDecoration: 'none',
              }}>Get started</Link>
            </div>

            <div style={{ border: '1px solid #e2e8f0', borderRadius: 20, padding: 36 }}>
              <div style={{ display: 'inline-block', background: '#f8fafc', color: '#64748b', fontSize: 10, fontWeight: 700, padding: '4px 12px', borderRadius: 99, marginBottom: 20, letterSpacing: 1, textTransform: 'uppercase' as const }}>Enterprise</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>Multi-Location</div>
              <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 28, lineHeight: 1.5 }}>Custom pricing for groups, chains, and dealerships.</p>
              <div style={{ fontSize: 32, fontWeight: 900, color: '#d97706', letterSpacing: -0.5, lineHeight: 1, marginBottom: 4 }}>Let&apos;s talk</div>
              <hr style={{ border: 'none', borderTop: '1px solid #f1f5f9', margin: '24px 0' }} />
              {['Multiple shop locations', 'Unlimited staff accounts', 'Everything in Starter', 'Priority support & onboarding', 'Custom integrations (DMS, fleet)'].map(f => (
                <div key={f} style={{ fontSize: 13, color: '#475569', padding: '6px 0', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ color: '#d97706', fontWeight: 700, flexShrink: 0 }}>✓</span> {f}
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
          <div style={{ width: 24, height: 24, background: 'linear-gradient(135deg,#d97706,#b45309)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 11 }}>A</div>
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
