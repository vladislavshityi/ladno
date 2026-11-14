import { DESCRIPTION_MAX, checkDescription } from '@/lib/validation'
import { useState } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { FormField } from '@/components/form-field'
import { useClassify, useUploadPhoto } from '../../hooks'
import { PhotoPicker } from '../photo-picker'
import { StepLayout } from '../step-layout'
import type { StepProps } from '../../wizard'

const MAX_PHOTOS = 3

export function DescribeStep({ data, setData, onNext }: StepProps) {
  const upload = useUploadPhoto()
  const classify = useClassify()
  const uploading = data.photos.some((p) => !p.id)
  const description = checkDescription(data.text)
  const [touched, setTouched] = useState(false)
  // A short text is an error; no text at all is fine when there is a photo.
  const canContinue = description.ok && (description.value !== null || data.photos.length > 0) && !uploading
  const error = touched && !description.ok ? description.error : undefined

  const addPhotos = (files: File[]) => {
    for (const file of files) {
      const preview = URL.createObjectURL(file)
      setData((d) => ({ ...d, photos: [...d.photos, { preview }] }))
      upload.mutate(file, {
        onSuccess: (photo) =>
          setData((d) => ({ ...d, photos: d.photos.map((p) => (p.preview === preview ? { ...p, id: photo.id } : p)) })),
        onError: () => setData((d) => ({ ...d, photos: d.photos.filter((p) => p.preview !== preview) })),
      })
    }
  }

  const submit = () =>
    classify.mutate(
      { text: description.ok ? (description.value ?? '') : '', photo_ids: data.photos.flatMap((p) => (p.id ? [p.id] : [])) },
      {
        onSuccess: (result) => {
          setData((d) => ({
            ...d,
            classification: result,
            category: d.presetCategory ?? (result.needs_manual_choice ? null : result.category),
            answers: {},
          }))
          onNext()
        },
      },
    )

  return (
    <StepLayout
      title="Что случилось?"
      description="Опишите проблему своими словами и по возможности добавьте фото — так мы точнее определим, кому писать."
      onNext={submit}
      nextDisabled={!canContinue}
      pending={classify.isPending}
      nextLabel={classify.isPending ? 'Определяем…' : 'Определить категорию'}
    >
      <FormField label="Описание" htmlFor="issue-text" hint="Например: в подъезде не горит свет на 3 этаже" error={error}>
        <Textarea
          id="issue-text"
          value={data.text}
          maxLength={DESCRIPTION_MAX}
          aria-invalid={Boolean(error)}
          onBlur={() => setTouched(true)}
          rows={4}
          autoFocus
          onChange={(e) => setData((d) => ({ ...d, text: e.target.value }))}
        />
      </FormField>
      <div className="grid gap-2">
        <p className="text-sm font-medium">Фото</p>
        <p className="text-sm text-muted-foreground">
          Фото помогут определить проблему и станут доказательством для УК и жилинспекции. По желанию, до {MAX_PHOTOS} шт.
        </p>
        <PhotoPicker
          photos={data.photos}
          max={MAX_PHOTOS}
          onAdd={addPhotos}
          onRemove={(i) => setData((d) => ({ ...d, photos: d.photos.filter((_, j) => j !== i) }))}
        />
      </div>
    </StepLayout>
  )
}
