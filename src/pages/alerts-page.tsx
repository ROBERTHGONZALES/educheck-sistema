import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bell, CheckCircle2, Phone } from 'lucide-react';
import { customFetch, useGetGrades } from '@workspace/api-client-react';

type AbsenceAlert = {
  studentId: number;
  studentName: string;
  dni: string;
  gradeName: string;
  sectionName: string;
  guardianPhone: string;
  consecutiveAbsences: number;
  absentSince: string;
  lastAttendanceDate: string | null;
};

type AlertsResponse = {
  threshold: number;
  recordedDays: number;
  alerts: AbsenceAlert[];
};

const formatDate = (iso: string | null) => {
  if (!iso) return 'Sin registro reciente';
  const [year, month, day] = iso.split('-');
  return `${day}/${month}/${year}`;
};

const severity = (days: number, threshold: number) =>
  days >= threshold + 2 ? 'danger' : days > threshold ? 'warn' : 'absent';

export default function AlertsPage() {
  const grades = useGetGrades();
  const [threshold, setThreshold] = useState(3);
  const [gradeId, setGradeId] = useState('');
  const [sectionId, setSectionId] = useState('');

  const params = new URLSearchParams({ threshold: String(threshold) });
  if (gradeId) params.set('gradeId', gradeId);
  if (sectionId) params.set('sectionId', sectionId);

  const alerts = useQuery({
    queryKey: ['director-alerts', threshold, gradeId, sectionId],
    queryFn: () => customFetch<AlertsResponse>(
      `/api/educheck/director/alerts?${params.toString()}`,
      { method: 'GET' },
    ),
  });

  const selectedGrade = grades.data?.find(grade => String(grade.id) === gradeId);
  const list = alerts.data?.alerts ?? [];
  const worst = list.reduce((max, item) => Math.max(max, item.consecutiveAbsences), 0);

  return <>
    <div className="page-heading">
      <div>
        <div className="eyebrow">Seguimiento</div>
        <h1>Alertas de inasistencia</h1>
        <p>Estudiantes que acumulan faltas seguidas, para avisar a su familia a tiempo.</p>
      </div>
    </div>

    <section className="panel filters-panel">
      <h2 className="panel-title">Filtros</h2>
      <div className="toolbar" style={{ marginTop: 16, marginBottom: 0 }}>
        <div className="field">
          <label htmlFor="alertThreshold">Faltas seguidas desde</label>
          <select
            id="alertThreshold"
            value={threshold}
            onChange={event => setThreshold(Number(event.target.value))}
            data-testid="select-alert-threshold"
          >
            {[2, 3, 4, 5, 7, 10].map(days => <option key={days} value={days}>{days} días</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="alertGrade">Grado</label>
          <select
            id="alertGrade"
            value={gradeId}
            onChange={event => { setGradeId(event.target.value); setSectionId(''); }}
            data-testid="select-alert-grade"
          >
            <option value="">Todos</option>
            {(grades.data ?? []).map(grade => <option key={grade.id} value={grade.id}>{grade.name}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="alertSection">Sección</label>
          <select
            id="alertSection"
            value={sectionId}
            onChange={event => setSectionId(event.target.value)}
            disabled={!selectedGrade}
            data-testid="select-alert-section"
          >
            <option value="">Todas</option>
            {(selectedGrade?.sections ?? []).map(section => <option key={section.id} value={section.id}>{section.name}</option>)}
          </select>
        </div>
      </div>
    </section>

    {alerts.isError
      ? <div className="error-state" role="alert" data-testid="status-alerts-error">
        <span>No se pudieron cargar las alertas.</span>
        <button className="btn" type="button" onClick={() => void alerts.refetch()}>Reintentar</button>
      </div>
      : alerts.isLoading
        ? <div className="panel"><div className="skeleton" /><div className="skeleton" style={{ marginTop: 10 }} /></div>
        : <>
          <div className="alert-summary">
            <div className="report-stat"><small>Alertas activas</small><strong data-testid="text-alert-count">{list.length}</strong></div>
            <div className="report-stat"><small>Racha más larga</small><strong>{worst ? `${worst} días` : '—'}</strong></div>
            <div className="report-stat"><small>Días con registro revisados</small><strong>{alerts.data?.recordedDays ?? 0}</strong></div>
          </div>
          <section className="panel">
            <h2 className="panel-title">Estudiantes con {threshold} o más faltas seguidas</h2>
            <p className="panel-subtitle">Se cuentan solo los días en que el colegio registró asistencia.</p>
            {list.length === 0
              ? <div className="empty-state" data-testid="empty-alerts">
                <div className="empty-icon"><CheckCircle2 /></div>
                <strong>Sin alertas por ahora</strong>
                <p>Ningún estudiante llega a {threshold} faltas seguidas con estos filtros.</p>
              </div>
              : <div className="table-wrap">
                <table className="data-table" data-testid="table-alerts">
                  <thead>
                    <tr>
                      <th>Estudiante</th>
                      <th>DNI</th>
                      <th>Grado y sección</th>
                      <th>Faltas seguidas</th>
                      <th>Faltando desde</th>
                      <th>Última asistencia</th>
                      <th>Apoderado</th>
                    </tr>
                  </thead>
                  <tbody>{list.map(item => <tr key={item.studentId} data-testid={`row-alert-${item.studentId}`}>
                    <td className="student-name">{item.studentName}</td>
                    <td>{item.dni}</td>
                    <td>{item.gradeName} · {item.sectionName}</td>
                    <td><span className={`tag ${severity(item.consecutiveAbsences, threshold)}`}><Bell size={12} />{item.consecutiveAbsences} días</span></td>
                    <td>{formatDate(item.absentSince)}</td>
                    <td>{formatDate(item.lastAttendanceDate)}</td>
                    <td><a className="alert-phone" href={`tel:${item.guardianPhone}`}><Phone size={12} style={{ verticalAlign: 'middle', marginRight: 6 }} />{item.guardianPhone}</a></td>
                  </tr>)}</tbody>
                </table>
              </div>}
          </section>
        </>}
  </>;
}
