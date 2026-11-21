import { BookOpen } from 'lucide-react'
import type { Assessment, V3Week, Week } from './api'

const phases = ['Fundamentos e consolidação', 'Aprofundamento e revisão', 'Aplicação e próximos passos']
const grid = 'grid md:grid-cols-2 gap-5'

function WeekCard({ week, names }: { week: Week | V3Week; names?: ReadonlyMap<string, string> }) {
  const details = 'estimated_minutes' in week ? week : null
  const Title = details ? 'h3' : 'h2'

  return <article className={details ? 'week week--v3' : 'week'}>
    <span className="eyebrow">SEMANA {String(week.week).padStart(2, '0')}</span>
    {details && <span className="week-duration">{details.estimated_minutes} min</span>}
    <Title>{week.title}</Title>
    <p>{week.objective}</p>
    {details && <strong className="week-activities">Atividades</strong>}
    <ul>{week.actions.map((action, index) => <li key={index}>{action}</li>)}</ul>
    <div className="week-deliverable"><BookOpen size={16} aria-hidden="true"/>
      <span>{details && <strong>Entregável</strong>}{week.deliverable}</span>
    </div>
    {details && <dl className="week-details">
      <div><dt>Competências</dt><dd>{details.competency_ids.map(id => names?.get(id)).join(', ')}</dd></div>
      <div><dt>Revisão</dt><dd>{details.review}</dd></div>
      {details.prerequisite_weeks.length > 0 && <div>
        <dt>Pré-requisitos</dt>
        <dd>{details.prerequisite_weeks.map(previous => 'Semana ' + previous).join(', ')}</dd>
      </div>}
    </dl>}
  </article>
}

export function StudyPlan({ assessment }: { assessment: Assessment }) {
  if (assessment.plan_version !== 3) {
    return <div className={grid}>{assessment.weeks.map(week => <WeekCard key={week.week} week={week}/>)}</div>
  }
  const names = new Map(assessment.gaps.map(gap => [gap.competency_id, gap.name]))

  return <div className="study-plan">
    {phases.map((title, index) => {
      const weeks = assessment.weeks.slice(index * 4, index * 4 + 4)
      const titleId = 'study-plan-title-' + (index + 1)
      const rangeId = 'study-plan-range-' + (index + 1)
      return <section aria-labelledby={titleId + ' ' + rangeId} key={title}>
        <div className="study-plan-group-heading">
          <h2 id={titleId}>{title}</h2>
          <p id={rangeId}>Semanas {weeks[0].week} a {weeks[weeks.length - 1].week}</p>
        </div>
        <div className={grid}>{weeks.map(week => <WeekCard key={week.week} week={week} names={names}/>)}</div>
      </section>
    })}
  </div>
}
