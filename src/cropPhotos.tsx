import credits from './cropPhotoCredits.json'

/**
 * Photograph support for the crop sections.
 *
 * Every image is a Wikimedia Commons file whose licence, photographer and source
 * page were read from the MediaWiki API by `scripts/build-crop-photos.py`, which
 * refuses to build if a licence is not on its allow list. The attribution in
 * `public/crops/credits.json` is therefore generated, not hand-written.
 *
 * Accessibility note: the crop thumbnails are decorative (the crop name sits right
 * beside them) so they carry `alt=""`. The banner is described by its visible
 * caption, so it also uses `alt=""` rather than repeating the caption twice to a
 * screen reader — the meaning lives in the figcaption, which is read out.
 */

type Credit = {
  caption: string
  file: string
  artist: string
  licence: string
  licence_url: string
  source: string
  original_width: number
}

const CREDITS = credits as Record<string, Credit>

export const hasCropPhoto = (cropId: string): boolean =>
  Object.prototype.hasOwnProperty.call(CREDITS, cropId)

export const cropPhoto = (cropId: string): Credit | undefined => CREDITS[cropId]

/** Responsive candidates, widest last so browsers can pick the smallest that fits. */
const srcSet = (cropId: string, widths: readonly number[]) =>
  widths.map((w) => `${import.meta.env.BASE_URL}crops/${cropId}-${w}.webp ${w}w`).join(', ')

export function CropThumb({ cropId }: { cropId: string }) {
  if (!hasCropPhoto(cropId)) return null
  return (
    <img
      className="crop-thumb"
      src={`${import.meta.env.BASE_URL}crops/${cropId}-160.webp`}
      width={44}
      height={28}
      alt=""
      loading="lazy"
      decoding="async"
    />
  )
}

export function CropPhoto({ cropId, cropName }: { cropId: string; cropName: string }) {
  const credit = cropPhoto(cropId)
  if (!credit) return null
  return (
    <figure className="crop-photo">
      <img
        src={`${import.meta.env.BASE_URL}crops/${cropId}-640.webp`}
        srcSet={srcSet(cropId, [640, 1024])}
        sizes="(max-width: 700px) 92vw, 520px"
        width={640}
        height={400}
        alt=""
        loading="lazy"
        decoding="async"
      />
      <figcaption>
        <span className="crop-photo-caption">
          <span className="crop-photo-crop">{cropName}</span>
          {credit.caption}
        </span>
        <span className="crop-photo-credit">
          Photo:{' '}
          <a href={credit.source} target="_blank" rel="noreferrer noopener">
            {credit.artist}
          </a>{' '}
          ·{' '}
          <a href={credit.licence_url} target="_blank" rel="noreferrer noopener">
            {credit.licence}
          </a>
        </span>
      </figcaption>
    </figure>
  )
}

