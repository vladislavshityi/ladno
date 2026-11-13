import { LegalDocument } from '../legal-document'
import { PRIVACY_SECTIONS } from '../privacy-sections'

export default function PrivacyPage() {
  return <LegalDocument title="Политика конфиденциальности" sections={PRIVACY_SECTIONS} />
}
