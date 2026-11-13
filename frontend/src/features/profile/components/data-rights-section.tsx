import { useState } from 'react'
import { Download, LogOut, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmDialog } from '@/components/confirm-dialog'
import { useAuth } from '@/features/auth/auth-context'
import { useDeleteAccount, useExportData } from '../hooks'

export function DataRightsSection() {
  const exportData = useExportData()
  const deleteAccount = useDeleteAccount()
  const { signOut } = useAuth()
  const navigate = useNavigate()
  const [confirming, setConfirming] = useState(false)

  return (
    <Card className="rounded-2xl border-0 shadow-sm ring-1 ring-border">
      <CardHeader>
        <CardTitle>Мои данные</CardTitle>
        <CardDescription>
          Что мы храним и зачем — в{' '}
          <Link to="/legal/privacy" className="text-primary hover:underline">
            политике конфиденциальности
          </Link>
          .
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => exportData.mutate()} disabled={exportData.isPending}>
          <Download /> Выгрузить мои данные
        </Button>
        <Button
          variant="outline"
          onClick={() => {
            signOut()
            navigate('/', { replace: true })
          }}
        >
          <LogOut /> Выйти
        </Button>
        <Button variant="destructive" onClick={() => setConfirming(true)}>
          <Trash2 /> Удалить аккаунт
        </Button>
      </CardContent>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Удалить аккаунт?"
        description="Будут безвозвратно удалены профиль, обращения, фото и квитанции. Это действие нельзя отменить."
        confirmLabel="Удалить аккаунт"
        onConfirm={() => deleteAccount.mutate()}
      />
    </Card>
  )
}
