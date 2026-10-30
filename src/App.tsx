import { lazy, Suspense, type FormEvent, type ReactNode, useEffect, useMemo, useRef, useState } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import ThemeToggle from '@/components/theme-toggle';
import { demoMailto } from '@/config';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import {
  useGetCsrfToken, useGetSession, getGetSessionQueryKey, useLogin, useLogout,
  useGetDirectorDashboard, useGetStudents, getGetStudentsQueryKey,
  useCreateStudent, useGetGrades, getGetGradesQueryKey, useCreateGrade, useCreateSection,
  useDeleteSection, useRegisterAttendance, useGetAttendance, getGetAttendanceQueryKey,
  useGetAttendanceReport, useExportAttendancePdf,
  getExportAttendancePdfQueryKey, useExportAttendanceXlsx, getExportAttendanceXlsxQueryKey,
  useListDirectorAssistants, getListDirectorAssistantsQueryKey, useCreateAssistant, useUpdateAssistantSections,
  useGetAssistantSections, getGetAssistantSectionsQueryKey, useGetAssistantSectionStudents,
  getGetAssistantSectionStudentsQueryKey, useImportAssistantStudents, useDownloadAssistantStudentCards,
  getDownloadAssistantStudentCardsQueryKey,
} from '@workspace/api-client-react';
import type { Assistant, AssistantSection, AttendanceRecord, SessionUser, Student, StudentImportResult } from '@workspace/api-client-react';
import {
  ArrowRight, Bell, BookOpen, CalendarDays, Check, CheckCircle2, ChevronRight,
  ClipboardList, Clock3, Download, FileSpreadsheet, FileText, GraduationCap, Laptop,
  LogOut, Menu, QrCode, Search, ShieldCheck, Smartphone, Tablet, Users, X, Plus, Save,
} from 'lucide-react';
import { Link, Route, Switch, useLocation, Router as WouterRouter } from 'wouter';

const queryClient = new QueryClient();
const limaDateParts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/Lima',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
}).formatToParts(new Date()).map(({ type, value }) => [type, value]));
const today = `${limaDateParts.year}-${limaDateParts.month}-${limaDateParts.day}`;
const AttendanceChart = lazy(() => import('@/components/attendance-chart'));
const AlertsPage = lazy(() => import('@/pages/alerts-page'));

function Logo({ light = false }: { light?: boolean }) {
  return <span className="logo" data-testid="brand-educheck">
    <img className="logo-mark" src="/brand-mark.png" alt="" width={512} height={365} />
    <span style={light ? { color: 'white' } : undefined}>EduCheck</span>
  </span>;
}

function DecorativeQr() {
  const size = 29;
  let seed = 7;
  const random = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  const inFinder = (x: number, y: number) =>
    (x < 8 && y < 8) || (x >= size - 8 && y < 8) || (x < 8 && y >= size - 8);
  const cells: Array<{ x: number; y: number }> = [];
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      if (!inFinder(x, y) && random() > 0.52) cells.push({ x, y });
    }
  }
  const finder = (x: number, y: number) => <g key={`finder-${x}-${y}`}>
    <rect x={x} y={y} width="7" height="7" fill="#34206A" />
    <rect x={x + 1} y={y + 1} width="5" height="5" fill="#fff" />
    <rect x={x + 2} y={y + 2} width="3" height="3" fill="#34206A" />
  </g>;
  return <svg className="qr-pattern" viewBox={`0 0 ${size} ${size}`} role="img" aria-label="Código QR ilustrativo">
    <rect width={size} height={size} fill="#fff" />
    <g fill="#34206A">{cells.map(cell => <rect key={`${cell.x}-${cell.y}`} x={cell.x} y={cell.y} width="1" height="1" />)}</g>
    {finder(0, 0)}{finder(size - 7, 0)}{finder(0, size - 7)}
  </svg>;
}

function Landing() {
  return <div className="landing-page">
    <header className="app-header">
      <Link href="/" className="logo" aria-label="EduCheck inicio"><Logo /></Link>
      <nav className="site-nav" aria-label="Navegación principal">
        <a href="#inicio" className="active">Inicio</a><a href="#como-funciona">Cómo funciona</a>
        <a href="#para-quien">Para quién</a><a href="#contacto">Contacto</a>
      </nav>
      <div className="header-actions">
        <ThemeToggle />
        <Link href="/ingresar" className="btn" data-testid="link-login">Ingresar</Link>
        {demoMailto && <a className="btn header-demo" href={demoMailto} data-testid="link-demo-header">Solicitar demostración</a>}
      </div>
    </header>
    <main id="inicio" className="wrap hero">
      <section>
        <h1>El ingreso de cada estudiante, registrado en <em>2 segundos</em></h1>
        <p id="como-funciona" className="hero-lead">EduCheck registra la asistencia con el QR del carnet y avisa a la dirección cuando un estudiante acumula 3 faltas seguidas.</p>
        <div className="hero-actions" id="contacto">
          {demoMailto
            ? <a className="btn btn-primary" href={demoMailto} data-testid="link-demo-request">Solicitar demostración <ArrowRight size={15} /></a>
            : <Link href="/ingresar" className="btn btn-primary" data-testid="link-enter-system">Ingresar al sistema <ArrowRight size={15} /></Link>}
          <a className="text-link" href="#para-quien"><span className="play-icon"><ArrowRight size={15} /></span>Ver cómo funciona</a>
        </div>
        <div className="device-line"><span>Funciona en:</span><span><Smartphone size={15} />Celular</span><span><Tablet size={15} />Tablet</span><span><Laptop size={15} />Computadora</span></div>
      </section>
      <div className="scene" aria-label="Vista ilustrativa del carnet de asistencia">
        <div className="scene-glow" /><div className="orbit orbit-three"><span className="orbit-dot" /></div>
        <div className="orbit"><span className="orbit-dot" /><span className="orbit-dot" style={{ top: '83%', left: '8%', width: 9, height: 9 }} /></div>
        <div className="orbit orbit-two"><span className="orbit-dot gold" /><span className="orbit-dot" style={{ top: '86%', left: '79%', width: 9, height: 9 }} /></div>
        <div className="demo-card">
          <div className="demo-card-top"><ShieldCheck size={15} /> EduCheck <span style={{ fontWeight: 500, color: '#6E6590' }}>Carnet de asistencia</span></div>
          <div className="demo-person"><span className="demo-avatar" /><span><b>Lucía Mamani</b><small>3.° B · Turno mañana</small></span></div>
          <div className="qr-demo"><DecorativeQr /><span className="scan-line" /></div>
          <div className="demo-caption">Código QR personal</div>
        </div>
        <div className="success-toast"><span className="toast-icon"><Check size={15} /></span><span><b>Asistencia registrada</b><small>Lucía Mamani · 07:42</small></span></div>
      </div>
    </main>
    <section className="feature-strip" id="para-quien">
      <div className="wrap"><p>Pensado para el día a día del colegio</p>
        <div className="feature-list">
          <span><QrCode />Carnet con QR</span><span><Users />Ingreso con DNI</span>
          <span><ShieldCheck />Alertas a la dirección</span><span><ClipboardList />Reportes por sección</span><span><GraduationCap />Director y auxiliares</span>
        </div>
      </div>
    </section>
  </div>;
}

function AuthPage() {
  const [, setLocation] = useLocation();
  const queryClient = useQueryClient();
  const csrf = useGetCsrfToken();
  const login = useLogin();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const submit = (event: FormEvent) => {
    event.preventDefault(); setError('');
    login.mutate({ data: { username: username.trim(), password } }, {
      onSuccess: async (user) => {
        queryClient.setQueryData(getGetSessionQueryKey(), user);
        setLocation(user.role === 'director' ? '/director/dashboard' : '/auxiliar/asistencia');
      },
      onError: (reason) => setError(reason instanceof Error ? reason.message : 'No pudimos validar el ingreso. Intenta nuevamente.'),
    });
  };
  return <div className="auth-wrap">
    <ThemeToggle floating />
    <section className="auth-card">
      <Link href="/" aria-label="Volver al inicio"><Logo /></Link>
      <h1>Ingresar a EduCheck</h1><p>Accede con tu cuenta del colegio para continuar.</p>
      {csrf.isError && <div className="notice" role="alert" data-testid="status-csrf-error">No se pudo preparar el acceso. Actualiza la página e inténtalo nuevamente.</div>}
      {error && <div className="error-state" role="alert" data-testid="status-login-error">{error}</div>}
      <form onSubmit={submit} aria-label="Formulario de ingreso">
        <div className="field"><label htmlFor="username">Usuario</label><input id="username" autoComplete="username" required value={username} onChange={e => setUsername(e.target.value)} placeholder="Tu nombre de usuario" data-testid="input-username" /></div>
        <div className="field"><label htmlFor="password">Contraseña</label><input id="password" type="password" autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} placeholder="Tu contraseña" data-testid="input-password" /></div>
        <button className="btn btn-primary" type="submit" disabled={login.isPending || csrf.isLoading} style={{ width: '100%', marginTop: 5 }} data-testid="button-login">
          {login.isPending ? 'Verificando acceso…' : 'Ingresar'} {!login.isPending && <ArrowRight size={16} />}
        </button>
      </form>
      <p style={{ margin: '18px 0 0', fontSize: 11 }}>Tu sesión se protege y expira automáticamente después de 30 minutos.</p>
    </section>
  </div>;
}

function LoadingPage() {
  return <div className="app-shell" style={{ display: 'grid', placeItems: 'center', padding: 24 }}>
    <div style={{ width: 'min(520px,100%)', display: 'grid', gap: 12 }} aria-label="Cargando"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div>
  </div>;
}

function Authenticated({ children, role }: { children: ReactNode; role?: 'director' | 'assistant' }) {
  const { data: session, isLoading, isError, refetch } = useGetSession();
  const [, setLocation] = useLocation();
  useEffect(() => {
    if (!isLoading && (isError || !session)) setLocation('/ingresar');
    else if (session && role && session.role !== role) setLocation(session.role === 'director' ? '/director/dashboard' : '/auxiliar/asistencia');
  }, [isLoading, isError, session, role, setLocation]);
  if (isLoading) return <LoadingPage />;
  if (isError || !session) return <LoadingPage />;
  if (role && session.role !== role) return <LoadingPage />;
  return <>{children}<button type="button" onClick={() => void refetch()} style={{ display: 'none' }} aria-hidden="true" /></>;
}

const directorLinks = [
  { href: '/director/dashboard', label: 'Resumen', icon: ClipboardList },
  { href: '/director/estudiantes', label: 'Estudiantes', icon: Users },
  { href: '/director/asistencias', label: 'Asistencias', icon: CalendarDays },
  { href: '/director/reportes', label: 'Reportes', icon: FileText },
  { href: '/director/alertas', label: 'Alertas', icon: Bell },
  { href: '/director/auxiliares', label: 'Auxiliares', icon: Users },
];

function ProductShell({ user, path, children }: { user: SessionUser; path: string; children: ReactNode }) {
  const [, setLocation] = useLocation();
  const logout = useLogout();
  const [logoutError, setLogoutError] = useState('');
  const assistant = user.role === 'assistant';
  const submitLogout = () => {
    setLogoutError('');
    logout.mutate(undefined, {
      onSuccess: () => {
        queryClient.removeQueries();
        setLocation('/');
      },
      onError: () => {
        setLogoutError('No se pudo cerrar la sesión. Comprueba que el servidor esté activo e inténtalo de nuevo.');
      },
    });
  };
  const links = assistant ? [
    { href: '/auxiliar/secciones', label: 'Mis secciones', icon: BookOpen },
    { href: '/auxiliar/asistencia', label: 'Registrar asistencia', icon: QrCode },
  ] : directorLinks;
  return <div className="app-layout">
    <aside className="sidebar">
      <Link href={assistant ? '/auxiliar/asistencia' : '/director/dashboard'}><Logo light /></Link>
      <div className="sidebar-school">{user.schoolName}<br />{assistant ? 'Asistente de puerta' : 'Panel de dirección'}</div>
      <div className="sidebar-label">Espacio de trabajo</div>
      <nav aria-label="Navegación del producto">{links.map(item => {
        const Icon = item.icon;
        return <Link href={item.href} key={item.href} className={`side-link ${path === item.href || (item.href === '/auxiliar/secciones' && path.startsWith('/auxiliar/secciones/')) ? 'active' : ''}`} data-testid={`link-nav-${item.href.split('/').pop()}`}>
          <Icon />{item.label}
        </Link>;
      })}</nav>
      <div className="sidebar-foot"><div className="sidebar-user"><span className="user-avatar">{initials(user.fullName)}</span><span><strong>{user.fullName}</strong><small>{assistant ? 'Asistente' : 'Director/a'}</small></span></div></div>
    </aside>
    <main className="main-area">
      <header className="topbar">
        <Link className="mobile-menu" href={assistant ? '/auxiliar/asistencia' : '/director/dashboard'}><Menu size={18} /> EduCheck</Link>
        <div className="topbar-school">{user.schoolName}</div>
        <ThemeToggle />
        <span className="topbar-user">{user.fullName}</span>
        <button className="logout-btn" type="button" onClick={submitLogout} disabled={logout.isPending} data-testid="button-logout"><LogOut size={15} />{logout.isPending ? 'Saliendo…' : 'Salir'}</button>
      </header>
      <div className="content">
        {logoutError && <div className="error-state" role="alert" data-testid="status-logout-error">
          <span>{logoutError}</span>
          <button className="btn" type="button" onClick={submitLogout} disabled={logout.isPending}>Reintentar</button>
        </div>}
        {children}
      </div>
    </main>
  </div>;
}

function initials(name: string) {
  return name.split(/\s+/).slice(0, 2).map(part => part.charAt(0)).join('').toUpperCase();
}

function QueryError({ message, retry }: { message: string; retry: () => void }) {
  return <div className="error-state" role="alert" data-testid="status-query-error"><span>{message}</span><button className="btn" type="button" onClick={retry} data-testid="button-retry">Reintentar</button></div>;
}

function PageHeading({ label, title, detail, children }: { label: string; title: string; detail: string; children?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow">{label}</div><h1>{title}</h1><p>{detail}</p></div>{children}</div>;
}

function DirectorDashboard() {
  const dashboard = useGetDirectorDashboard();
  const summary = dashboard.data;
  const metrics = [
    { label: 'Estudiantes activos', value: summary?.activeStudents, icon: Users },
    { label: 'Presentes hoy', value: summary?.presentToday, icon: CheckCircle2 },
    { label: 'Ausentes hoy', value: summary?.absentToday, icon: CalendarDays },
    { label: 'Asistencia de hoy', value: summary ? `${summary.attendanceRate}%` : undefined, icon: Clock3 },
  ];
  return <>
    <PageHeading label="Vista general" title="Resumen del colegio" detail="Un vistazo a la asistencia de hoy." />
    {dashboard.isError ? <QueryError message="No fue posible cargar el resumen del colegio." retry={() => void dashboard.refetch()} /> : <>
      <section className="metrics-grid" aria-label="Resumen de asistencia">
        {metrics.map((item, index) => { const Icon = item.icon; return <div className="metric" key={item.label} data-testid={`metric-dashboard-${index}`}>
          <div className="metric-label">{item.label}</div><div className="metric-value">{dashboard.isLoading ? '—' : (item.value ?? '—')}</div><div className="metric-icon"><Icon /></div>
        </div>; })}
      </section>
      {dashboard.isLoading ? <div className="skeleton" /> : summary && <div className="dashboard-lower">
        <section className="panel"><h2 className="panel-title">Asistencia por turno</h2><p className="panel-subtitle">Estudiantes que registraron su llegada hoy.</p>
          {summary.shifts.length ? summary.shifts.map((shift, index) => <div className="shift-row" key={shift.shift} data-testid={`row-shift-${index}`}>
            <span className="shift-mark"><Clock3 size={17} /></span><span className="shift-copy"><strong>{shift.shift === 'morning' ? 'Mañana' : 'Tarde'}</strong><small>Registros de hoy</small></span><span className="shift-count">{shift.present}</span>
          </div>) : <EmptyState icon={<Clock3 />} title="Aún no hay registros por turno" detail="Los registros de asistencia aparecerán aquí." />}
        </section>
        <section className="panel"><h2 className="panel-title">Accesos directos</h2><p className="panel-subtitle">Continúa con una tarea de dirección.</p><div className="shortcut-list">
          <Link className="shortcut" href="/director/estudiantes">Gestionar estudiantes <ChevronRight size={16} /></Link>
          <Link className="shortcut" href="/director/alertas">Ver alertas de inasistencia <ChevronRight size={16} /></Link>
          <Link className="shortcut" href="/director/asistencias">Consultar asistencias <ChevronRight size={16} /></Link>
          <Link className="shortcut" href="/director/reportes">Ver reportes <ChevronRight size={16} /></Link>
        </div></section>
      </div>}
    </>}
  </>;
}

function EmptyState({ icon, title, detail }: { icon: ReactNode; title: string; detail: string }) {
  return <div className="empty-state"><span className="empty-icon">{icon}</span><strong>{title}</strong><p>{detail}</p></div>;
}

function StudentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [gradeFilter, setGradeFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [gradeName, setGradeName] = useState('');
  const [sectionName, setSectionName] = useState('');
  const [sectionGradeId, setSectionGradeId] = useState('');
  const [error, setError] = useState('');
  const [newStudent, setNewStudent] = useState<Student | null>(null);
  const grades = useGetGrades();
  const params = useMemo(() => ({
    ...(search.trim() ? { search: search.trim() } : {}),
    ...(gradeFilter ? { gradeId: Number(gradeFilter) } : {}),
    ...(sectionFilter ? { sectionId: Number(sectionFilter) } : {}),
  }), [search, gradeFilter, sectionFilter]);
  const students = useGetStudents(params);
  const createStudent = useCreateStudent();
  const createGrade = useCreateGrade();
  const createSection = useCreateSection();
  const deleteSection = useDeleteSection();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: getGetStudentsQueryKey() });
    void queryClient.invalidateQueries({ queryKey: getGetGradesQueryKey() });
  };
  const formData = (event: FormEvent<HTMLFormElement>) => Object.fromEntries(new FormData(event.currentTarget).entries());
  const submitStudent = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('');
    const form = event.currentTarget;
    const f = formData(event) as Record<string, string>;
    createStudent.mutate({ data: { dni: f.dni, firstName: f.firstName.trim(), lastName: f.lastName.trim(), gradeId: Number(f.gradeId), sectionId: Number(f.sectionId), guardianPhone: f.guardianPhone.trim() } }, {
      onSuccess: student => { setNewStudent(student); form.reset(); refresh(); },
      onError: () => setError('No se pudo registrar al estudiante. Revisa los datos e inténtalo nuevamente.'),
    });
  };
  const submitGrade = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('');
    createGrade.mutate({ data: { name: gradeName.trim() } }, {
      onSuccess: () => { setGradeName(''); refresh(); },
      onError: () => setError('No se pudo crear el grado.'),
    });
  };
  const submitSection = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError('');
    if (!sectionGradeId) return;
    createSection.mutate({ data: { gradeId: Number(sectionGradeId), name: sectionName.trim() } }, {
      onSuccess: () => { setSectionName(''); refresh(); },
      onError: () => setError('No se pudo crear la sección.'),
    });
  };
  const visibleSections = grades.data?.find(g => g.id === Number(gradeFilter))?.sections ?? [];
  return <>
    <PageHeading label="Directorio escolar" title="Estudiantes" detail="Registra estudiantes y organiza grados y secciones." />
    {error && <div className="error-state" role="alert" style={{ marginBottom: 16 }} data-testid="status-student-error">{error}<button aria-label="Cerrar aviso" onClick={() => setError('')}><X size={16} /></button></div>}
    <section className="panel">
      <h2 className="panel-title">Registrar estudiante</h2><p className="panel-subtitle">El carnet QR se genera de forma segura al guardar.</p>
      <form onSubmit={submitStudent}>
        <div className="form-grid">
          <div className="field"><label htmlFor="dni">DNI (8 dígitos)</label><input id="dni" name="dni" required inputMode="numeric" pattern="[0-9]{8}" maxLength={8} placeholder="00000000" data-testid="input-student-dni" /></div>
          <div className="field"><label htmlFor="guardianPhone">Teléfono del apoderado</label><input id="guardianPhone" name="guardianPhone" required type="tel" placeholder="Número de contacto" data-testid="input-guardian-phone" /></div>
          <div className="field"><label htmlFor="firstName">Nombres</label><input id="firstName" name="firstName" required placeholder="Nombres del estudiante" data-testid="input-student-firstname" /></div>
          <div className="field"><label htmlFor="lastName">Apellidos</label><input id="lastName" name="lastName" required placeholder="Apellidos del estudiante" data-testid="input-student-lastname" /></div>
          <div className="field"><label htmlFor="studentGrade">Grado</label><select id="studentGrade" name="gradeId" required defaultValue="" data-testid="select-student-grade"><option value="" disabled>Seleccionar grado</option>{(grades.data ?? []).map(grade => <option key={grade.id} value={grade.id}>{grade.name}</option>)}</select></div>
          <div className="field"><label htmlFor="studentSection">Sección</label><select id="studentSection" name="sectionId" required defaultValue="" data-testid="select-student-section"><option value="" disabled>Seleccionar sección</option>{(grades.data ?? []).flatMap(grade => grade.sections.map(section => <option key={section.id} value={section.id}>{grade.name} · {section.name}</option>))}</select></div>
        </div>
        <div className="form-actions"><button type="submit" className="btn btn-primary" disabled={createStudent.isPending || grades.isLoading || !grades.data?.length} data-testid="button-create-student">{createStudent.isPending ? 'Guardando…' : 'Registrar estudiante'}</button></div>
      </form>
      {grades.isLoading && <div className="skeleton" style={{ marginTop: 15 }} />}
      {grades.isError && <QueryError message="No se pudieron cargar los grados." retry={() => void grades.refetch()} />}
      {newStudent && <div className="panel" style={{ marginTop: 18 }} data-testid="status-student-created">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', gap: 12 }}><div><h3 className="panel-title">Carnet generado</h3><p className="panel-subtitle">{newStudent.firstName} {newStudent.lastName} · {newStudent.gradeName} {newStudent.sectionName}</p></div><button type="button" className="logout-btn" aria-label="Cerrar carnet" onClick={() => setNewStudent(null)}><X size={17} /></button></div>
        <div style={{ width: 130, height: 130, padding: 8, border: '1px solid var(--ec-line)', borderRadius: 12, background: '#fff' }} dangerouslySetInnerHTML={{ __html: newStudent.qrSvg }} aria-label={`QR del carnet de ${newStudent.firstName}`} />
        <small style={{ display: 'block', marginTop: 8, color: 'var(--ec-muted)' }}>El código contiene un token seguro, no el DNI.</small>
      </div>}
    </section>
    <div className="management-grid">
      <section className="panel"><h2 className="panel-title">Grados y secciones</h2><p className="panel-subtitle">Administra la estructura de tus aulas.</p>
        <form className="toolbar" onSubmit={submitGrade}><div className="field" style={{ margin: 0 }}><label htmlFor="gradeName">Nuevo grado</label><input id="gradeName" value={gradeName} onChange={e => setGradeName(e.target.value)} required placeholder="Ej. 1.° de secundaria" data-testid="input-grade-name" /></div><button className="btn btn-primary" type="submit" disabled={createGrade.isPending} data-testid="button-create-grade">{createGrade.isPending ? 'Creando…' : 'Crear grado'}</button></form>
        <form className="toolbar" onSubmit={submitSection}><div className="field" style={{ margin: 0 }}><label htmlFor="sectionGrade">Grado</label><select id="sectionGrade" value={sectionGradeId} onChange={e => setSectionGradeId(e.target.value)} required data-testid="select-section-grade"><option value="">Seleccionar grado</option>{(grades.data ?? []).map(g => <option key={g.id} value={g.id}>{g.name}</option>)}</select></div><div className="field" style={{ margin: 0 }}><label htmlFor="sectionName">Nueva sección</label><input id="sectionName" value={sectionName} onChange={e => setSectionName(e.target.value)} required placeholder="Ej. A" data-testid="input-section-name" /></div><button className="btn" type="submit" disabled={!sectionGradeId || createSection.isPending} data-testid="button-create-section">{createSection.isPending ? 'Creando…' : 'Agregar'}</button></form>
        {grades.isLoading ? <div className="skeleton" /> : grades.data?.length ? grades.data.map(grade => <div className="grade-card" key={grade.id} data-testid={`card-grade-${grade.id}`}><div className="grade-head"><span>{grade.name}</span><GraduationCap size={16} /></div>
          {grade.sections.length ? grade.sections.map(section => <span className="section-chip" key={section.id}>{section.name}<button type="button" aria-label={`Eliminar sección ${section.name}`} onClick={() => { if (window.confirm(`¿Eliminar la sección ${section.name}?`)) deleteSection.mutate({ sectionId: section.id }, { onSuccess: refresh, onError: () => setError('No se pudo eliminar la sección. Puede tener estudiantes asignados.') }); }} data-testid={`button-delete-section-${section.id}`}><X size={12} /></button></span>) : <small style={{ color: 'var(--ec-muted)' }}>Sin secciones todavía</small>}
        </div>) : <EmptyState icon={<GraduationCap />} title="Todavía no hay grados" detail="Crea un grado para comenzar a registrar estudiantes." />}
      </section>
      <section className="panel"><h2 className="panel-title">Buscar estudiantes</h2><p className="panel-subtitle">Filtra el directorio registrado.</p>
        <div className="toolbar"><div className="field search-field"><label htmlFor="studentSearch">Nombre o DNI</label><div style={{ position: 'relative' }}><Search size={15} style={{ position: 'absolute', left: 12, top: 13, color: 'var(--ec-muted)' }} /><input id="studentSearch" value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar estudiante…" style={{ paddingLeft: 35 }} data-testid="input-student-search" /></div></div>
          <div className="field"><label htmlFor="gradeFilter">Grado</label><select id="gradeFilter" value={gradeFilter} onChange={e => { setGradeFilter(e.target.value); setSectionFilter(''); }} data-testid="filter-student-grade"><option value="">Todos</option>{(grades.data ?? []).map(g => <option key={g.id} value={g.id}>{g.name}</option>)}</select></div>
          <div className="field"><label htmlFor="sectionFilter">Sección</label><select id="sectionFilter" value={sectionFilter} onChange={e => setSectionFilter(e.target.value)} data-testid="filter-student-section"><option value="">Todas</option>{visibleSections.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
        </div>
        <StudentsTable students={students.data ?? []} isLoading={students.isLoading} isError={students.isError} retry={() => void students.refetch()} />
      </section>
    </div>
  </>;
}

function StudentsTable({ students, isLoading, isError, retry }: { students: Student[]; isLoading: boolean; isError: boolean; retry: () => void }) {
  if (isError) return <QueryError message="No se pudo cargar la lista de estudiantes." retry={retry} />;
  if (isLoading) return <div style={{ display: 'grid', gap: 8 }}><div className="skeleton" /><div className="skeleton" /></div>;
  if (!students.length) return <EmptyState icon={<Users />} title="No encontramos estudiantes" detail="Ajusta los filtros o registra un estudiante nuevo." />;
  return <div className="table-wrap"><table className="data-table"><thead><tr><th>Estudiante</th><th>DNI</th><th>Grado / sección</th><th>Apoderado</th><th>Estado</th></tr></thead><tbody>
    {students.map(student => <tr key={student.id} data-testid={`row-student-${student.id}`}><td className="student-name">{student.firstName} {student.lastName}</td><td>{student.dni}</td><td>{student.gradeName} · {student.sectionName}</td><td>{student.guardianPhone}</td><td><span className={`tag ${student.active ? 'active' : 'absent'}`}>{student.active ? 'Activo' : 'Inactivo'}</span></td></tr>)}
  </tbody></table></div>;
}

function DirectorAssistantsPage() {
  const queryClient = useQueryClient();
  const assistants = useListDirectorAssistants();
  const grades = useGetGrades();
  const createAssistant = useCreateAssistant();
  const updateSections = useUpdateAssistantSections();
  const [sectionIds, setSectionIds] = useState<number[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editingSections, setEditingSections] = useState<number[]>([]);
  const [error, setError] = useState('');
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: getListDirectorAssistantsQueryKey() });
    void queryClient.invalidateQueries({ queryKey: getGetAssistantSectionsQueryKey() });
  };
  const toggle = (current: number[], id: number) => current.includes(id) ? current.filter(value => value !== id) : [...current, id];
  const allSections = grades.data?.flatMap(grade => grade.sections.map(section => ({
    id: section.id, gradeName: grade.name, name: section.name,
  }))) ?? [];
  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget).entries()) as Record<string, string>;
    setError('');
    createAssistant.mutate({ data: {
      username: values.username.trim(), fullName: values.fullName.trim(),
      password: values.password, sectionIds,
    } }, {
      onSuccess: () => {
        (event.currentTarget as HTMLFormElement | null)?.reset();
        setSectionIds([]);
        invalidate();
      },
      onError: () => setError('No se pudo crear el auxiliar. Revisa el usuario, la contraseña y las asignaciones.'),
    });
  };
  const saveSections = (assistant: Assistant) => {
    setError('');
    updateSections.mutate({ assistantId: assistant.id, data: { sectionIds: editingSections } }, {
      onSuccess: () => { setEditingId(null); invalidate(); },
      onError: () => setError('No se pudieron actualizar las secciones asignadas.'),
    });
  };
  return <>
    <PageHeading label="Equipo escolar" title="Auxiliares" detail="Crea cuentas de acceso y organiza las secciones a cargo de cada auxiliar.">
      <span className="count-pill" data-testid="count-director-assistants">{assistants.data?.length ?? '—'} cuentas</span>
    </PageHeading>
    {error && <div className="error-state" role="alert" style={{ marginBottom: 16 }} data-testid="status-assistant-error">{error}<button type="button" aria-label="Cerrar aviso" onClick={() => setError('')}><X size={16} /></button></div>}
    <section className="panel assistant-create-panel">
      <div className="section-kicker"><span className="empty-icon"><Plus /></span><div><h2 className="panel-title">Agregar auxiliar</h2><p className="panel-subtitle">La contraseña inicial debe tener al menos 12 caracteres.</p></div></div>
      <form onSubmit={submit} data-testid="form-create-assistant">
        <div className="form-grid">
          <div className="field"><label htmlFor="assistantFullName">Nombre completo</label><input id="assistantFullName" name="fullName" required maxLength={150} placeholder="Nombre y apellidos" data-testid="input-assistant-fullname" /></div>
          <div className="field"><label htmlFor="assistantUsername">Usuario</label><input id="assistantUsername" name="username" required maxLength={150} autoComplete="off" placeholder="Nombre de usuario" data-testid="input-assistant-username" /></div>
          <div className="field"><label htmlFor="assistantPassword">Contraseña inicial</label><input id="assistantPassword" name="password" type="password" required minLength={12} autoComplete="new-password" placeholder="Mínimo 12 caracteres" data-testid="input-assistant-password" /></div>
        </div>
        <div className="field"><label>Secciones asignadas</label>
          {grades.isLoading ? <div className="skeleton" /> : grades.isError ? <QueryError message="No fue posible cargar los grados y secciones." retry={() => void grades.refetch()} /> : allSections.length ? <div className="section-picker" data-testid="picker-create-assistant-sections">
            {grades.data?.map(grade => grade.sections.map(section => <label className={`section-option ${sectionIds.includes(section.id) ? 'selected' : ''}`} key={section.id}>
              <input type="checkbox" checked={sectionIds.includes(section.id)} onChange={() => setSectionIds(current => toggle(current, section.id))} data-testid={`checkbox-new-assistant-section-${section.id}`} />
              <span><strong>{grade.name} · {section.name}</strong><small>{section.name}</small></span>
            </label>))}
          </div> : <EmptyState icon={<GraduationCap />} title="No hay secciones disponibles" detail="Crea grados y secciones antes de asignar un auxiliar." />}
        </div>
        <div className="form-actions"><button type="submit" className="btn btn-primary" disabled={createAssistant.isPending || !sectionIds.length || grades.isError} data-testid="button-create-assistant">{createAssistant.isPending ? 'Creando cuenta…' : 'Crear auxiliar'} {!createAssistant.isPending && <ArrowRight size={15} />}</button><span className="helper-text">{sectionIds.length ? `${sectionIds.length} sección${sectionIds.length === 1 ? '' : 'es'} seleccionada${sectionIds.length === 1 ? '' : 's'}` : 'Selecciona al menos una sección.'}</span></div>
      </form>
    </section>
    <section className="assistant-list-section">
      <div className="list-heading"><div><div className="eyebrow">Directorio</div><h2>Auxiliares registrados</h2></div><span className="list-meta">{assistants.data?.length ?? 0} en el colegio</span></div>
      {assistants.isLoading ? <div className="assistant-skeletons"><div className="skeleton" /><div className="skeleton" /></div>
        : assistants.isError ? <QueryError message="No fue posible cargar los auxiliares." retry={() => void assistants.refetch()} />
          : !assistants.data?.length ? <div className="panel"><EmptyState icon={<Users />} title="Aún no hay auxiliares" detail="Crea la primera cuenta para asignar la atención de secciones." /></div>
            : <div className="assistant-cards">{assistants.data.map(assistant => {
              const isEditing = editingId === assistant.id;
              const assignedIds = isEditing ? editingSections : assistant.sections.map(section => section.id);
              return <article className="assistant-card" key={assistant.id} data-testid={`card-assistant-${assistant.id}`}>
                <div className="assistant-card-head"><span className="assistant-avatar">{initials(assistant.fullName)}</span><div className="assistant-identity"><strong data-testid={`text-assistant-name-${assistant.id}`}>{assistant.fullName}</strong><small>@{assistant.username}</small></div>
                  {!isEditing ? <button type="button" className="btn btn-small" onClick={() => { setEditingId(assistant.id); setEditingSections(assistant.sections.map(s => s.id)); }} data-testid={`button-edit-assistant-sections-${assistant.id}`}>Editar secciones</button>
                    : <div className="inline-actions"><button type="button" className="btn btn-small" onClick={() => saveSections(assistant)} disabled={updateSections.isPending} data-testid={`button-save-assistant-sections-${assistant.id}`}><Save size={14} />{updateSections.isPending ? 'Guardando…' : 'Guardar'}</button><button type="button" className="quiet-button" onClick={() => setEditingId(null)} data-testid={`button-cancel-assistant-sections-${assistant.id}`}>Cancelar</button></div>}
                </div>
                {isEditing ? <div className="section-picker compact" data-testid={`picker-assistant-sections-${assistant.id}`}>
                  {allSections.map(section => <label className={`section-option ${assignedIds.includes(section.id) ? 'selected' : ''}`} key={section.id}><input type="checkbox" checked={assignedIds.includes(section.id)} onChange={() => setEditingSections(current => toggle(current, section.id))} data-testid={`checkbox-assistant-${assistant.id}-section-${section.id}`} /><span><strong>{section.gradeName} · {section.name}</strong></span></label>)}
                </div> : <div className="assistant-card-bottom"><div className="assigned-chips">{assistant.sections.length ? assistant.sections.map(section => <span className="assigned-chip" key={section.id} data-testid={`chip-assistant-${assistant.id}-section-${section.id}`}>{section.gradeName} · {section.name}</span>) : <span className="muted-copy">Sin secciones asignadas</span>}</div><span className="student-total">{assistant.sections.reduce((sum, section) => sum + section.studentCount, 0)} estudiantes</span></div>}
              </article>;
            })}</div>}
    </section>
  </>;
}

function AssistantSectionsPage() {
  const sections = useGetAssistantSections();
  return <>
    <PageHeading label="Espacio del auxiliar" title="Mis secciones" detail="Entra a un aula para revisar estudiantes, importar la nómina o descargar sus carnets." />
    {sections.isLoading ? <div className="section-grid">{[1, 2].map(i => <div className="panel" key={i}><div className="skeleton" /><div className="skeleton" style={{ marginTop: 10 }} /></div>)}</div>
      : sections.isError ? <QueryError message="No fue posible cargar tus secciones asignadas." retry={() => void sections.refetch()} />
        : !sections.data?.length ? <section className="panel"><EmptyState icon={<BookOpen />} title="Todavía no tienes secciones asignadas" detail="Pide a dirección que te asigne una o más aulas para comenzar." /></section>
          : <div className="section-grid" data-testid="list-assistant-sections">{sections.data.map((section: AssistantSection) => <Link href={`/auxiliar/secciones/${section.id}`} className="classroom-card" key={section.id} data-testid={`link-assistant-section-${section.id}`}>
            <div className="classroom-index">AULA <span>{String(section.id).padStart(2, '0')}</span></div><div className="classroom-grade">{section.gradeName}</div><div className="classroom-section">Sección <strong>{section.name}</strong></div><div className="classroom-card-foot"><span>{section.studentCount} estudiantes</span><span className="classroom-arrow"><ArrowRight size={17} /></span></div>
          </Link>)}</div>}
  </>;
}

function getImportValidationErrors(reason: unknown): unknown[] {
  if (!reason || typeof reason !== 'object') return [];
  const payload = reason as { data?: { errors?: unknown }; errors?: unknown };
  const errors = payload.data?.errors ?? payload.errors;
  return Array.isArray(errors) ? errors : [];
}

function AssistantSectionDetail({ rawSectionId }: { rawSectionId?: string }) {
  const sectionId = Number(rawSectionId);
  const validId = Number.isInteger(sectionId) && sectionId > 0;
  const assigned = useGetAssistantSections();
  const allowed = validId && !!assigned.data?.some(section => section.id === sectionId);
  const queryClient = useQueryClient();
  const students = useGetAssistantSectionStudents(validId ? sectionId : 0, { query: { enabled: allowed, queryKey: getGetAssistantSectionStudentsQueryKey(validId ? sectionId : 0) } });
  const cards = useDownloadAssistantStudentCards(validId ? sectionId : 0, { query: { enabled: false, queryKey: getDownloadAssistantStudentCardsQueryKey(validId ? sectionId : 0) } });
  const importStudents = useImportAssistantStudents();
  const [file, setFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<StudentImportResult | null>(null);
  const [validationErrors, setValidationErrors] = useState<unknown[]>([]);
  const [fileError, setFileError] = useState('');
  const [downloadError, setDownloadError] = useState('');
  const section = assigned.data?.find(item => item.id === sectionId);
  const invalidateStudents = () => {
    void queryClient.invalidateQueries({ queryKey: getGetAssistantSectionStudentsQueryKey(sectionId) });
    void queryClient.invalidateQueries({ queryKey: getGetAssistantSectionsQueryKey() });
  };
  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null;
    setImportResult(null); setValidationErrors([]); setFileError('');
    if (selected && !selected.name.toLowerCase().endsWith('.xlsx')) {
      setFile(null); setFileError('Selecciona un archivo de Excel con extensión .xlsx.'); event.target.value = ''; return;
    }
    setFile(selected);
  };
  const submitImport = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file || !allowed) return;
    setFileError(''); setValidationErrors([]); setImportResult(null);
    importStudents.mutate({ sectionId, data: { file } }, {
      onSuccess: result => { setImportResult(result); setFile(null); const input = document.getElementById('sectionImportFile') as HTMLInputElement | null; if (input) input.value = ''; invalidateStudents(); },
      onError: reason => {
        const errors = getImportValidationErrors(reason);
        setValidationErrors(errors);
        setFileError(errors.length ? 'El archivo contiene filas que requieren corrección.' : 'No se pudo importar el archivo. Verifica el formato e inténtalo nuevamente.');
      },
    });
  };
  const downloadCards = async () => {
    setDownloadError('');
    try {
      const result = await cards.refetch();
      if (!result.data) throw new Error('PDF no disponible');
      const url = URL.createObjectURL(result.data);
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = `carnets-${section?.gradeName ?? 'seccion'}-${section?.name ?? sectionId}.pdf`;
      document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
    } catch {
      setDownloadError('No se pudo descargar el PDF de carnets. Inténtalo nuevamente.');
    }
  };
  if (!validId) return <><PageHeading label="Sección" title="Identificador inválido" detail="No encontramos una sección con ese identificador." /><section className="panel"><EmptyState icon={<X />} title="Revisa el enlace" detail="Vuelve a Mis secciones y elige un aula asignada." /><Link className="btn" href="/auxiliar/secciones" data-testid="link-invalid-section-back">Volver a mis secciones</Link></section></>;
  if (assigned.isLoading) return <><PageHeading label="Aula" title="Cargando sección…" detail="Estamos verificando tus asignaciones." /><div className="skeleton" /></>;
  if (assigned.isError) return <><PageHeading label="Aula" title="No se pudo cargar" detail="Verifica tu conexión e inténtalo nuevamente." /><QueryError message="No fue posible validar tus secciones asignadas." retry={() => void assigned.refetch()} /></>;
  if (!allowed || !section) return <><PageHeading label="Sección" title="Aula no disponible" detail="Esta sección no está entre tus asignaciones actuales." /><section className="panel"><EmptyState icon={<ShieldCheck />} title="Acceso no disponible" detail="Solo puedes consultar aulas que dirección te haya asignado." /><Link className="btn" href="/auxiliar/secciones" data-testid="link-unassigned-section-back">Volver a mis secciones</Link></section></>;
  return <>
    <div className="detail-back"><Link href="/auxiliar/secciones" className="back-link" data-testid="link-back-assistant-sections"><ChevronRight size={15} /> Mis secciones</Link></div>
    <PageHeading label={`${section.gradeName} · Sección ${section.name}`} title="Estudiantes del aula" detail={`${section.studentCount} estudiantes asignados a esta sección.`}>
      <button type="button" className="btn btn-primary" onClick={() => void downloadCards()} disabled={cards.isFetching} data-testid="button-download-section-cards"><Download size={16} />{cards.isFetching ? 'Preparando PDF…' : 'Descargar carnets'}</button>
    </PageHeading>
    {downloadError && <div className="error-state" role="alert" data-testid="status-cards-download-error">{downloadError}<button type="button" onClick={() => setDownloadError('')} aria-label="Cerrar aviso"><X size={16} /></button></div>}
    <section className="panel import-panel">
      <div className="import-head"><span className="import-icon"><FileSpreadsheet /></span><div><h2 className="panel-title">Importar estudiantes</h2><p className="panel-subtitle">Sube la nómina en Excel (.xlsx). El servidor valida cada fila antes de guardar.</p></div></div>
      <form onSubmit={submitImport} className="import-form">
        <div className="file-drop"><FileSpreadsheet size={22} /><label htmlFor="sectionImportFile">Archivo .xlsx</label><input id="sectionImportFile" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={onFileChange} data-testid="input-section-students-xlsx" /><span>{file?.name ?? 'Selecciona el archivo de tu dispositivo'}</span></div>
        <button type="submit" className="btn" disabled={!file || importStudents.isPending} data-testid="button-import-section-students">{importStudents.isPending ? 'Validando e importando…' : 'Importar archivo'} <ArrowRight size={15} /></button>
      </form>
      {fileError && <div className="import-message error" role="alert" data-testid="status-student-import-error">{fileError}</div>}
      {validationErrors.length > 0 && <div className="validation-list" role="alert" data-testid="list-import-row-errors"><strong>Errores de validación por fila</strong>{validationErrors.map((issue, index) => {
        const item = issue && typeof issue === 'object' ? issue as Record<string, unknown> : null;
        const row = item?.row ?? item?.fila ?? item?.rowNumber;
        const description = item?.message ?? item?.error ?? item?.detail ?? JSON.stringify(issue);
        return <div className="validation-row" key={index}><span>{row !== undefined ? `Fila ${String(row)}` : 'Validación'}</span><p>{String(description)}</p></div>;
      })}</div>}
      {importResult && <div className="import-success" role="status" data-testid="status-student-import-result"><CheckCircle2 size={19} /><div><strong>Importación procesada</strong><p>{importResult.total} filas revisadas. {importResult.created} creados, {importResult.updated} actualizados, {importResult.existing} sin cambios. Se conservaron {importResult.qrPreserved} códigos QR.</p></div></div>}
    </section>
    <section className="panel section-students-panel">
      <div className="list-heading"><div><div className="eyebrow">Nómina del aula</div><h2>Estudiantes</h2></div><span className="list-meta">{students.data?.length ?? 0} registros</span></div>
      {students.isLoading ? <div style={{ display: 'grid', gap: 8 }}><div className="skeleton" /><div className="skeleton" /></div>
        : students.isError ? <QueryError message="No se pudo cargar la lista de estudiantes de esta sección." retry={() => void students.refetch()} />
          : <StudentsTable students={students.data ?? []} isLoading={false} isError={false} retry={() => void students.refetch()} />}
    </section>
  </>;
}

function AttendancePage() {
  const [date, setDate] = useState(today);
  const [shift, setShift] = useState('');
  const [gradeId, setGradeId] = useState('');
  const [sectionId, setSectionId] = useState('');
  const [dni, setDni] = useState('');
  const grades = useGetGrades();
  const params = useMemo(() => ({
    date,
    ...(shift ? { shift: shift as 'morning' | 'afternoon' } : {}),
    ...(gradeId ? { gradeId: Number(gradeId) } : {}),
    ...(sectionId ? { sectionId: Number(sectionId) } : {}),
    ...(dni ? { dni } : {}),
  }), [date, shift, gradeId, sectionId, dni]);
  const attendance = useGetAttendance(params);
  const sections = grades.data?.find(g => g.id === Number(gradeId))?.sections ?? [];
  return <>
    <PageHeading label="Control de asistencia" title="Asistencias" detail="Consulta presentes y ausentes por día, turno, aula o DNI." />
    <section className="panel filters-panel"><h2 className="panel-title">Filtros de consulta</h2><div className="toolbar" style={{ marginTop: 16, marginBottom: 0 }}>
      <div className="field"><label htmlFor="attendanceDate">Fecha</label><input id="attendanceDate" type="date" value={date} onChange={e => setDate(e.target.value)} data-testid="filter-attendance-date" /></div>
      <div className="field"><label htmlFor="attendanceShift">Turno</label><select id="attendanceShift" value={shift} onChange={e => setShift(e.target.value)} data-testid="filter-attendance-shift"><option value="">Todos</option><option value="morning">Mañana</option><option value="afternoon">Tarde</option></select></div>
      <div className="field"><label htmlFor="attendanceGrade">Grado</label><select id="attendanceGrade" value={gradeId} onChange={e => { setGradeId(e.target.value); setSectionId(''); }} data-testid="filter-attendance-grade"><option value="">Todos</option>{(grades.data ?? []).map(g => <option value={g.id} key={g.id}>{g.name}</option>)}</select></div>
      <div className="field"><label htmlFor="attendanceSection">Sección</label><select id="attendanceSection" value={sectionId} onChange={e => setSectionId(e.target.value)} data-testid="filter-attendance-section"><option value="">Todas</option>{sections.map(s => <option value={s.id} key={s.id}>{s.name}</option>)}</select></div>
      <div className="field"><label htmlFor="attendanceDni">DNI</label><input id="attendanceDni" inputMode="numeric" pattern="[0-9]{0,8}" maxLength={8} value={dni} onChange={e => setDni(e.target.value)} placeholder="8 dígitos" data-testid="filter-attendance-dni" /></div>
    </div></section>
    {attendance.isError ? <QueryError message="No se pudo consultar la asistencia. Revisa la fecha e inténtalo de nuevo." retry={() => void attendance.refetch()} /> :
      attendance.isLoading ? <div className="panel"><div className="skeleton" /><div className="skeleton" style={{ marginTop: 10 }} /></div> : attendance.data && <>
        <section className="panel" style={{ marginBottom: 16 }}><h2 className="panel-title">Presentes <span style={{ color: 'var(--ec-muted)', font: '500 12px Inter' }}>· {attendance.data.records.length}</span></h2>
          {attendance.data.records.length ? <AttendanceTable records={attendance.data.records} /> : <EmptyState icon={<CheckCircle2 />} title="Sin registros de llegada" detail="No hay estudiantes presentes con los filtros seleccionados." />}
        </section>
        <section className="panel"><h2 className="panel-title">Ausentes <span style={{ color: 'var(--ec-muted)', font: '500 12px Inter' }}>· {attendance.data.absentStudents.length}</span></h2>
          {attendance.data.absentStudents.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Estudiante</th><th>DNI</th><th>Grado / sección</th><th>Estado</th></tr></thead><tbody>{attendance.data.absentStudents.map((s, i) => <tr key={s.studentId} data-testid={`row-absent-${s.studentId}-${i}`}><td className="student-name">{s.studentName}</td><td>{s.dni}</td><td>{s.gradeName} · {s.sectionName}</td><td><span className="tag absent">Ausente</span></td></tr>)}</tbody></table></div> : <EmptyState icon={<CheckCircle2 />} title="Sin ausencias" detail="No hay ausencias para los filtros seleccionados." />}
        </section>
      </>}
  </>;
}

function AttendanceTable({ records }: { records: AttendanceRecord[] }) {
  return <div className="table-wrap"><table className="data-table"><thead><tr><th>Estudiante</th><th>DNI</th><th>Grado / sección</th><th>Hora</th><th>Turno</th><th>Registro</th><th>Registró</th></tr></thead><tbody>{records.map((r, i) => <tr key={`${r.studentId}-${r.time}-${i}`} data-testid={`row-present-${r.studentId}-${i}`}><td className="student-name">{r.studentName}</td><td>{r.dni}</td><td>{r.gradeName} · {r.sectionName}</td><td>{r.time}</td><td>{r.shift === 'morning' ? 'Mañana' : 'Tarde'}</td><td>{r.source === 'qr' ? 'QR' : 'DNI'}</td><td>{r.attendedBy}</td></tr>)}</tbody></table></div>;
}

function ReportsPage() {
  const [from, setFrom] = useState(`${today.slice(0, 7)}-01`);
  const [to, setTo] = useState(today);
  const [gradeId, setGradeId] = useState('');
  const [sectionId, setSectionId] = useState('');
  const [exportError, setExportError] = useState('');
  const grades = useGetGrades();
  const params = useMemo(() => ({ from, to, ...(gradeId ? { gradeId: Number(gradeId) } : {}), ...(sectionId ? { sectionId: Number(sectionId) } : {}) }), [from, to, gradeId, sectionId]);
  const report = useGetAttendanceReport(params);
  const pdf = useExportAttendancePdf(params, { query: { enabled: false, queryKey: getExportAttendancePdfQueryKey(params) } });
  const xlsx = useExportAttendanceXlsx(params, { query: { enabled: false, queryKey: getExportAttendanceXlsxQueryKey(params) } });
  const sections = grades.data?.find(g => g.id === Number(gradeId))?.sections ?? [];
  const download = async (format: 'pdf' | 'xlsx') => {
    setExportError('');
    const result = format === 'pdf' ? await pdf.refetch() : await xlsx.refetch();
    if (result.isError || !result.data) { setExportError('No se pudo generar el archivo. Inténtalo nuevamente.'); return; }
    const url = URL.createObjectURL(result.data);
    const anchor = document.createElement('a');
    anchor.href = url; anchor.download = `educheck-reporte-${from}-${to}.${format}`;
    document.body.appendChild(anchor); anchor.click(); anchor.remove(); URL.revokeObjectURL(url);
  };
  return <>
    <PageHeading label="Análisis escolar" title="Reportes" detail="Revisa porcentajes de asistencia y ausencia por periodo y aula." />
    <section className="panel filters-panel"><h2 className="panel-title">Periodo del reporte</h2><div className="toolbar" style={{ marginTop: 16, marginBottom: 0 }}>
      <div className="field"><label htmlFor="reportFrom">Desde</label><input id="reportFrom" type="date" value={from} max={to} onChange={e => setFrom(e.target.value)} data-testid="filter-report-from" /></div>
      <div className="field"><label htmlFor="reportTo">Hasta</label><input id="reportTo" type="date" value={to} min={from} onChange={e => setTo(e.target.value)} data-testid="filter-report-to" /></div>
      <div className="field"><label htmlFor="reportGrade">Grado</label><select id="reportGrade" value={gradeId} onChange={e => { setGradeId(e.target.value); setSectionId(''); }} data-testid="filter-report-grade"><option value="">Todos</option>{(grades.data ?? []).map(g => <option key={g.id} value={g.id}>{g.name}</option>)}</select></div>
      <div className="field"><label htmlFor="reportSection">Sección</label><select id="reportSection" value={sectionId} onChange={e => setSectionId(e.target.value)} data-testid="filter-report-section"><option value="">Todas</option>{sections.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
      <button className="btn" type="button" onClick={() => void download('pdf')} disabled={pdf.isFetching || report.isLoading} data-testid="button-export-pdf"><FileText size={15} />{pdf.isFetching ? 'Preparando…' : 'Exportar PDF'}</button>
      <button className="btn" type="button" onClick={() => void download('xlsx')} disabled={xlsx.isFetching || report.isLoading} data-testid="button-export-xlsx"><FileSpreadsheet size={15} />{xlsx.isFetching ? 'Preparando…' : 'Exportar XLSX'}</button>
    </div></section>
    {exportError && <div className="error-state" role="alert" style={{ marginBottom: 15 }} data-testid="status-export-error">{exportError}</div>}
    {report.isError ? <QueryError message="No se pudo generar el reporte de asistencia." retry={() => void report.refetch()} /> : report.isLoading ? <div className="panel"><div className="skeleton" /><div className="skeleton" style={{ marginTop: 10 }} /></div> : report.data && <>
      <section className="panel" style={{ marginBottom: 16 }}><h2 className="panel-title">Resumen del periodo</h2><p className="panel-subtitle">{report.data.from} — {report.data.to} · {report.data.recordedDays} días registrados</p>
        <div className="report-summary">
          <div className="report-stat"><small>Asistencia</small><strong>{report.data.attendanceRate}%</strong><div className="report-bar"><span style={{ width: `${Math.min(100, Math.max(0, report.data.attendanceRate))}%` }} /></div></div>
          <div className="report-stat"><small>Ausencia</small><strong>{report.data.absenceRate}%</strong><div className="report-bar"><span style={{ width: `${Math.min(100, Math.max(0, report.data.absenceRate))}%`, background: 'var(--ec-neutral)' }} /></div></div>
          <div className="report-stat"><small>Registros presentes</small><strong>{report.data.presentCount}</strong><small style={{ marginTop: 5 }}>Ausencias registradas: {report.data.absenceCount}</small></div>
        </div>
      </section>
      {report.data.groups.length > 0 && <section className="panel chart-panel" style={{ marginBottom: 16 }}>
        <h2 className="panel-title">Porcentajes por sección</h2>
        <p className="panel-subtitle">Comparación de asistencia e inasistencia en los días con registros.</p>
        <Suspense fallback={<div className="report-chart chart-loading" aria-label="Cargando gráfico" />}>
          <AttendanceChart groups={report.data.groups} />
        </Suspense>
      </section>}
      <section className="panel"><h2 className="panel-title">Detalle por sección</h2><p className="panel-subtitle">Comparativo de asistencia en el periodo.</p>
        {report.data.groups.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Grado</th><th>Sección</th><th>Presentes</th><th>Ausencias</th><th>Asistencia</th><th>Ausencia</th></tr></thead><tbody>{report.data.groups.map((group, i) => <tr key={`${group.gradeName}-${group.sectionName}`} data-testid={`row-report-${i}`}><td>{group.gradeName}</td><td>{group.sectionName}</td><td>{group.presentCount}</td><td>{group.absenceCount}</td><td><span className="tag active">{group.attendanceRate}%</span></td><td><span className="tag absent">{group.absenceRate}%</span></td></tr>)}</tbody></table></div> : <EmptyState icon={<ClipboardList />} title="Sin datos en este periodo" detail="Prueba con otro periodo o filtro de aula." />}
      </section>
    </>}
  </>;
}

function AssistantAttendance() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<'qr' | 'dni'>('qr');
  const [shift, setShift] = useState<'morning' | 'afternoon'>('morning');
  const [qrCode, setQrCode] = useState('');
  const [dni, setDni] = useState('');
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null);
  const [cameraError, setCameraError] = useState('');
  const [cameraOn, setCameraOn] = useState(false);
  const scannerRef = useRef<import('html5-qrcode').Html5Qrcode | null>(null);
  const register = useRegisterAttendance();
  useEffect(() => {
    let active = true;
    let scanner: import('html5-qrcode').Html5Qrcode | null = null;
    const start = async () => {
      if (!cameraOn || mode !== 'qr') return;
      try {
        const { Html5Qrcode } = await import('html5-qrcode');
        if (!active) return;
        scanner = new Html5Qrcode('educheck-qr-reader', { verbose: false });
        scannerRef.current = scanner;
        await scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 220, height: 220 } },
          decodedText => {
            if (!active) return;
            setQrCode(decodedText);
            setCameraError('');
            setCameraOn(false);
          },
          () => undefined,
        );
        if (!active && scanner.isScanning) await scanner.stop();
      } catch {
        if (active) {
          setCameraOn(false);
          setCameraError('No se pudo iniciar el escáner. Verifica el permiso de cámara e inténtalo nuevamente.');
        }
      }
    };
    void start();
    return () => {
      active = false;
      const currentScanner = scanner ?? scannerRef.current;
      if (currentScanner) {
        if (currentScanner.isScanning) {
          void currentScanner.stop().then(() => currentScanner.clear()).catch(() => undefined);
        } else {
          try { currentScanner.clear(); } catch { /* The scanner may not have mounted yet. */ }
        }
      }
      scannerRef.current = null;
    };
  }, [cameraOn, mode]);
  const submit = (event: FormEvent) => {
    event.preventDefault(); setMessage(null);
    const payload = mode === 'qr' ? { qrCode: qrCode.trim(), shift } : { dni: dni.trim(), shift };
    register.mutate({ data: payload }, {
      onSuccess: record => {
        setMessage({ kind: 'success', text: `Llegada registrada para ${record.studentName} · ${record.time}.` });
        setQrCode(''); setDni('');
        void queryClient.invalidateQueries({ queryKey: getGetAttendanceQueryKey({ date: today }) });
      },
      onError: error => setMessage({ kind: 'error', text: error instanceof Error ? error.message : 'No se pudo registrar. Verifica el código y vuelve a intentar.' }),
    });
  };
  const changeMode = (next: 'qr' | 'dni') => { setMode(next); setMessage(null); setCameraOn(false); setCameraError(''); };
  return <>
    <PageHeading label="Punto de ingreso" title="Registrar asistencia" detail="Valida la llegada del estudiante con su carnet o DNI." />
    <div className="scan-layout">
      <section className="panel"><h2 className="panel-title">Registro de llegada</h2><p className="panel-subtitle">Selecciona el turno y escanea el carnet o ingresa el DNI.</p>
        <div className="field"><label htmlFor="scanShift">Turno</label><select id="scanShift" value={shift} onChange={e => setShift(e.target.value as 'morning' | 'afternoon')} data-testid="select-attendance-shift"><option value="morning">Mañana</option><option value="afternoon">Tarde</option></select></div>
        <div className="scan-mode" role="tablist" aria-label="Método de registro">
          <button type="button" className={mode === 'qr' ? 'selected' : ''} onClick={() => changeMode('qr')} role="tab" aria-selected={mode === 'qr'} data-testid="tab-scan-qr"><QrCode size={15} style={{ verticalAlign: 'middle', marginRight: 6 }} />Escanear QR</button>
          <button type="button" className={mode === 'dni' ? 'selected' : ''} onClick={() => changeMode('dni')} role="tab" aria-selected={mode === 'dni'} data-testid="tab-scan-dni">Ingresar DNI</button>
        </div>
        <form onSubmit={submit}>
          {mode === 'qr' ? <>
            <div className="camera-frame">{cameraOn ? <><div id="educheck-qr-reader" aria-label="Escáner QR de asistencia" /><span className="scan-frame" /></> : <p><QrCode size={26} style={{ display: 'block', margin: '0 auto 10px' }} />Apunta la cámara al código QR del carnet.</p>}</div>
            {cameraError && <p role="status" style={{ color: 'var(--ec-muted)', fontSize: 11 }}>{cameraError}</p>}
            <button type="button" className="btn" style={{ marginTop: 12 }} onClick={() => { setCameraError(''); setCameraOn(value => !value); }} data-testid="button-camera">{cameraOn ? 'Detener cámara' : 'Activar cámara'}</button>
            <div className="scan-token" role="status" data-testid="status-qr-token">{qrCode ? 'Código leído. Confirma para registrar la llegada.' : 'El código solo se captura con la cámara.'}</div>
          </> : <div className="field"><label htmlFor="manualDni">DNI del estudiante</label><input id="manualDni" value={dni} onChange={e => setDni(e.target.value.replace(/\D/g, '').slice(0, 8))} required inputMode="numeric" pattern="[0-9]{8}" maxLength={8} placeholder="8 dígitos" data-testid="input-attendance-dni" /><small style={{ color: 'var(--ec-muted)', fontSize: 11 }}>Ingresa el DNI de 8 dígitos registrado en el colegio.</small></div>}
          {message && <div className={`attendance-result ${message.kind === 'error' ? 'error' : ''}`} role="status" data-testid={`status-attendance-${message.kind}`}>{message.text}</div>}
          <button className="btn btn-primary" type="submit" disabled={register.isPending || (mode === 'qr' ? qrCode.trim().length < 16 : dni.length !== 8)} style={{ width: '100%', marginTop: 17 }} data-testid="button-register-attendance">
            {register.isPending ? 'Registrando…' : 'Registrar llegada'} {!register.isPending && <Check size={16} />}
          </button>
        </form>
      </section>
      <aside className="panel"><span className="empty-icon"><ShieldCheck /></span><h2 className="panel-title">Registro confiable</h2><p className="panel-subtitle">El sistema valida cada llegada con el colegio y la sesión activa.</p>
        <div className="notice-box"><strong style={{ color: 'var(--ec-deep)' }}>Código QR seguro</strong><br />El código del carnet usa un token aleatorio. No contiene el DNI del estudiante.</div>
        <div className="notice-box" style={{ marginTop: 11 }}><strong style={{ color: 'var(--ec-deep)' }}>Sesión protegida</strong><br />Los registros son verificados por el servidor. Si tu sesión vence, vuelve a ingresar.</div>
      </aside>
    </div>
  </>;
}

function ProductRoute({ role, path, children }: { role: 'director' | 'assistant'; path: string; children: (user: SessionUser) => ReactNode }) {
  const { data } = useGetSession();
  return <Authenticated role={role}><ProductShell user={data!} path={path}>{children(data!)}</ProductShell></Authenticated>;
}

function Router() {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>
    <Switch>
      <Route path="/" component={Landing} />
      <Route path="/ingresar" component={AuthPage} />
      <Route path="/director/dashboard">{() => <ProductRoute role="director" path="/director/dashboard">{() => <DirectorDashboard />}</ProductRoute>}</Route>
      <Route path="/director/estudiantes">{() => <ProductRoute role="director" path="/director/estudiantes">{() => <StudentsPage />}</ProductRoute>}</Route>
      <Route path="/director/asistencias">{() => <ProductRoute role="director" path="/director/asistencias">{() => <AttendancePage />}</ProductRoute>}</Route>
      <Route path="/director/reportes">{() => <ProductRoute role="director" path="/director/reportes">{() => <ReportsPage />}</ProductRoute>}</Route>
      <Route path="/director/alertas">{() => <ProductRoute role="director" path="/director/alertas">{() => <Suspense fallback={<LoadingPage />}><AlertsPage /></Suspense>}</ProductRoute>}</Route>
      <Route path="/director/auxiliares">{() => <ProductRoute role="director" path="/director/auxiliares">{() => <DirectorAssistantsPage />}</ProductRoute>}</Route>
      <Route path="/auxiliar/secciones">{() => <ProductRoute role="assistant" path="/auxiliar/secciones">{() => <AssistantSectionsPage />}</ProductRoute>}</Route>
      <Route path="/auxiliar/secciones/:sectionId">{params => <ProductRoute role="assistant" path={`/auxiliar/secciones/${params.sectionId}`}>{() => <AssistantSectionDetail rawSectionId={params.sectionId} />}</ProductRoute>}</Route>
      <Route path="/auxiliar/asistencia">{() => <ProductRoute role="assistant" path="/auxiliar/asistencia">{() => <AssistantAttendance />}</ProductRoute>}</Route>
      <Route component={NotFound} />
    </Switch>
  </ErrorBoundary>;
}

function App() {
  return <QueryClientProvider client={queryClient}>
    <TooltipProvider><WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}><Router /></WouterRouter><Toaster /></TooltipProvider>
  </QueryClientProvider>;
}

export default App;
