import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'Legal Fact Checker',
    short_name: 'LegalCheck',
    description: 'AI 기반 법령 검증 및 팩트체크 서비스',
    start_url: '/',
    display: 'standalone',
    background_color: '#ffffff',
    theme_color: '#000000',
    icons: [
      {
        src: '/icon512_maskable.svg',
        sizes: '512x512',
        type: 'image/svg+xml',
        purpose: 'maskable'
      },
      {
        src: '/icon512_rounded.svg',
        sizes: '512x512',
        type: 'image/svg+xml',
        purpose: 'any'
      }
    ]
  }
}
