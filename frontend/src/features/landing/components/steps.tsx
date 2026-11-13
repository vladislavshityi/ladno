const STEPS = [
  { title: 'Расскажите', text: 'Опишите проблему или загрузите квитанцию.' },
  { title: 'Получите разбор', text: 'Покажем адресата, сроки и пояснения к начислениям.' },
  { title: 'Действуйте', text: 'Скопируйте готовое письмо и подайте его в один клик.' },
]

export function Steps() {
  return (
    <section aria-label="Как это работает" className="space-y-5">
      <h2 className="text-2xl font-semibold tracking-tight">Как это работает</h2>
      <ol className="grid gap-4 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <li key={step.title} className="flex gap-3">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
              {i + 1}
            </span>
            <div>
              <p className="font-medium">{step.title}</p>
              <p className="text-sm text-muted-foreground">{step.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
