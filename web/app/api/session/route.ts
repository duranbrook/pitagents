export const maxDuration = 60

export async function POST(request: Request) {
  const contentType = request.headers.get('content-type') ?? ''
  const body = await request.arrayBuffer()

  const upstream = await fetch('https://api.openai.com/v1/realtime/calls', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      'Content-Type': contentType,
    },
    body,
  })

  const sdp = await upstream.text()
  return new Response(sdp, {
    status: upstream.status,
    headers: {
      'Content-Type': upstream.headers.get('content-type') ?? 'application/sdp',
    },
  })
}
