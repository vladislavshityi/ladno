import { LegalDocument } from '../legal-document'
import { CONSENT_SECTIONS } from '../consent-sections'

export default function ConsentTextPage() {
  return <LegalDocument title="Согласие на обработку персональных данных" sections={CONSENT_SECTIONS} />
}
