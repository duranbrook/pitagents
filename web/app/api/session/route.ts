export const maxDuration = 60

const OPENAI_REALTIME_URL = 'https://api.openai.com/v1/realtime/calls'
const MAX_ATTEMPTS = 3

export async function POST(request: Request) {
  const contentType = request.headers.get('content-type') ?? ''
  const body = await request.arrayBuffer()

  let lastStatus = 502
  let lastBody = ''
  let lastContentType = 'text/plain'

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    let upstream: Response
    try {
      upstream = await fetch(OPENAI_REALTIME_URL, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
          'Content-Type': contentType,
        },
        body,
      })
    } catch (err) {
      console.error(`[session] fetch attempt ${attempt} failed:`, err)
      if (attempt < MAX_ATTEMPTS) continue
      return new Response('Failed to reach OpenAI Realtime', { status: 502 })
    }

    const responseBody = await upstream.text()
    lastStatus = upstream.status
    lastBody = responseBody
    lastContentType = upstream.headers.get('content-type') ?? 'application/sdp'

    if (upstream.ok) {
      console.log('[session] OpenAI Realtime SDP exchange OK', { attempt, status: upstream.status, bodyLen: responseBody.length })
      return new Response(responseBody, {
        status: upstream.status,
        headers: { 'Content-Type': lastContentType },
      })
    }

    // Retry on 5xx (OpenAI gateway blips); pass through 4xx immediately
    console.error(`[session] OpenAI Realtime error attempt ${attempt}/${MAX_ATTEMPTS}`, {
      status: upstream.status,
      body: responseBody.slice(0, 300),
    })
    if (upstream.status < 500 || attempt === MAX_ATTEMPTS) break

    // Brief back-off before retry (500ms, 1000ms)
    await new Promise(r => setTimeout(r, attempt * 500))
  }

  return new Response(lastBody, {
    status: lastStatus,
    headers: { 'Content-Type': lastContentType },
  })
}
