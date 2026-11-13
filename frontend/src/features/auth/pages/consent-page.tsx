import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { LogoMark } from '@/components/logo'
import { useAcceptConsent, useAuthConfig, useMe } from '../hooks'

export default function ConsentPage() {
  const { data: me } = useMe()
  const { data: config } = useAuthConfig()
  const accept = useAcceptConsent()
  const navigate = useNavigate()
  const [agreed, setAgreed] = useState(false)

  if (me && !me.consent_required) return <Navigate to="/issues/new" replace />

  return (
    <div className="flex min-h-svh items-center justify-center px-4 py-10">
      <div className="w-full max-w-md animate-in fade-in-0 slide-in-from-bottom-2 duration-500">
        <LogoMark className="mx-auto mb-6 size-12" />
        <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
          <CardHeader className="text-center">
            <CardTitle className="text-xl">Прежде чем начать</CardTitle>
            <CardDescription>
              Чтобы сохранять ваш дом, обращения и квитанции, нам нужно ваше согласие на обработку персональных данных.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-5">
            <ul className="space-y-1.5 text-sm text-muted-foreground">
              <li>Данные хранятся на сервере и доступны только вам.</li>
              <li>ФИО, телефон и квартира в языковую модель не уходят.</li>
              <li>Выгрузить данные или удалить аккаунт можно в любой момент.</li>
            </ul>
            <div className="flex items-start gap-3">
              <Checkbox id="agree" checked={agreed} onCheckedChange={(v) => setAgreed(v === true)} className="mt-0.5" />
              <Label htmlFor="agree" className="block text-sm leading-snug font-normal">
                Я прочитал(а){' '}
                <Link to="/legal/privacy" target="_blank" className="text-primary hover:underline">
                  политику конфиденциальности
                </Link>{' '}
                и даю{' '}
                <Link to="/legal/consent" target="_blank" className="text-primary hover:underline">
                  согласие на обработку персональных данных
                </Link>
              </Label>
            </div>
            <Button
              size="lg"
              disabled={!agreed || !config || accept.isPending}
              onClick={() => accept.mutate(config!.consent_version, { onSuccess: () => navigate('/issues/new', { replace: true }) })}
            >
              {accept.isPending && <Loader2 className="animate-spin" />}
              Продолжить
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
