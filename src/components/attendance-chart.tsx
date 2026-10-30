import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { AttendanceReportGroup } from '@workspace/api-client-react';

export default function AttendanceChart({ groups }: { groups: AttendanceReportGroup[] }) {
  return <div className="report-chart" data-testid="chart-attendance-by-section">
    <ResponsiveContainer width="100%" height={280}>
      <BarChart
        data={groups.map(group => ({ ...group, label: `${group.gradeName} · ${group.sectionName}` }))}
        margin={{ top: 8, right: 12, left: -15, bottom: 8 }}
      >
        <CartesianGrid stroke="rgba(113,113,122,.28)" strokeDasharray="4 4" />
        <XAxis dataKey="label" tick={{ fill: '#71717a', fontSize: 11 }} stroke="rgba(113,113,122,.4)" />
        <YAxis domain={[0, 100]} tick={{ fill: '#71717a', fontSize: 11 }} stroke="rgba(113,113,122,.4)" tickFormatter={value => `${value}%`} />
        <Tooltip
          cursor={{ fill: 'rgba(113,113,122,.12)' }}
          contentStyle={{ background: 'var(--t-card-solid)', border: '1px solid var(--t-line-strong)', borderRadius: 14, color: 'var(--t-fg)', fontSize: 12 }}
          formatter={value => [`${Number(value).toFixed(1)}%`]}
        />
        <Bar dataKey="attendanceRate" name="Asistencia" fill="#3b82f6" radius={[8, 8, 0, 0]} />
        <Bar dataKey="absenceRate" name="Inasistencia" fill="#71717a" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  </div>;
}
