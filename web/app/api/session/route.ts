export const maxDuration = 60

export async function POST(request: Request) {
  const contentType = request.headers.get('content-type') ?? ''
  const body = await request.arrayBuffer()

  let upstream: Response
  try {
    upstream = await fetch('https://api.openai.com/v1/realtime/calls', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        'Content-Type': contentType,
      },
      body,
    })
  } catch (err) {
    console.error('[session] fetch to OpenAI Realtime failed:', err)
    return new Response('Failed to reach OpenAI Realtime', { status: 502 })
  }

  const sdp = await upstream.text()

  if (!upstream.ok) {
    console.error('[session] OpenAI Realtime error', {
      status: upstream.status,
      body: sdp.slice(0, 500),
    })
  } else {
    console.log('[session] OpenAI Realtime SDP exchange OK', { status: upstream.status, bodyLen: sdp.length })
  }

  return new Response(sdp, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'application/sdp',
    },
  })
}
