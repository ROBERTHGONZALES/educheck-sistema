from django.db import migrations


TRIGGERS = (
    """
    CREATE TRIGGER educheck_section_school_bi
    BEFORE INSERT ON educheck_sections FOR EACH ROW
    BEGIN
        DECLARE grade_school BIGINT DEFAULT NULL;
        SELECT colegio_id INTO grade_school
        FROM educheck_grades WHERE id = NEW.grade_id;
        IF grade_school IS NULL OR grade_school <> NEW.colegio_id THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El grado y la sección deben pertenecer al mismo colegio';
        END IF;
    END
    """,
    """
    CREATE TRIGGER educheck_section_school_bu
    BEFORE UPDATE ON educheck_sections FOR EACH ROW
    BEGIN
        DECLARE grade_school BIGINT DEFAULT NULL;
        SELECT colegio_id INTO grade_school
        FROM educheck_grades WHERE id = NEW.grade_id;
        IF grade_school IS NULL OR grade_school <> NEW.colegio_id THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El grado y la sección deben pertenecer al mismo colegio';
        END IF;
    END
    """,
    """
    CREATE TRIGGER educheck_student_school_bi
    BEFORE INSERT ON educheck_students FOR EACH ROW
    BEGIN
        DECLARE grade_school BIGINT DEFAULT NULL;
        DECLARE section_school BIGINT DEFAULT NULL;
        DECLARE section_grade BIGINT DEFAULT NULL;
        SELECT colegio_id INTO grade_school
        FROM educheck_grades WHERE id = NEW.grade_id;
        SELECT colegio_id, grade_id INTO section_school, section_grade
        FROM educheck_sections WHERE id = NEW.section_id;
        IF grade_school IS NULL OR section_school IS NULL
           OR grade_school <> NEW.colegio_id
           OR section_school <> NEW.colegio_id
           OR section_grade <> NEW.grade_id THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El estudiante, grado y sección deben pertenecer al mismo colegio';
        END IF;
    END
    """,
    """
    CREATE TRIGGER educheck_student_school_bu
    BEFORE UPDATE ON educheck_students FOR EACH ROW
    BEGIN
        DECLARE grade_school BIGINT DEFAULT NULL;
        DECLARE section_school BIGINT DEFAULT NULL;
        DECLARE section_grade BIGINT DEFAULT NULL;
        SELECT colegio_id INTO grade_school
        FROM educheck_grades WHERE id = NEW.grade_id;
        SELECT colegio_id, grade_id INTO section_school, section_grade
        FROM educheck_sections WHERE id = NEW.section_id;
        IF grade_school IS NULL OR section_school IS NULL
           OR grade_school <> NEW.colegio_id
           OR section_school <> NEW.colegio_id
           OR section_grade <> NEW.grade_id THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El estudiante, grado y sección deben pertenecer al mismo colegio';
        END IF;
    END
    """,
    """
    CREATE TRIGGER educheck_attendance_school_bi
    BEFORE INSERT ON educheck_attendance FOR EACH ROW
    BEGIN
        DECLARE student_school BIGINT DEFAULT NULL;
        DECLARE account_school BIGINT DEFAULT NULL;
        SELECT colegio_id INTO student_school
        FROM educheck_students WHERE id = NEW.student_id;
        SELECT colegio_id INTO account_school
        FROM educheck_accounts WHERE id = NEW.attended_by_id;
        IF student_school IS NULL OR account_school IS NULL
           OR student_school <> NEW.colegio_id
           OR account_school <> NEW.colegio_id THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El registro, estudiante y usuario deben pertenecer al mismo colegio';
        END IF;
    END
    """,
    """
    CREATE TRIGGER educheck_attendance_school_bu
    BEFORE UPDATE ON educheck_attendance FOR EACH ROW
    BEGIN
        DECLARE student_school BIGINT DEFAULT NULL;
        DECLARE account_school BIGINT DEFAULT NULL;
        SELECT colegio_id INTO student_school
        FROM educheck_students WHERE id = NEW.student_id;
        SELECT colegio_id INTO account_school
        FROM educheck_accounts WHERE id = NEW.attended_by_id;
        IF student_school IS NULL OR account_school IS NULL
           OR student_school <> NEW.colegio_id
           OR account_school <> NEW.colegio_id THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'El registro, estudiante y usuario deben pertenecer al mismo colegio';
        END IF;
    END
    """,
)

VIEWS = (
    """
    CREATE OR REPLACE VIEW vw_educheck_students_by_section AS
    SELECT
        st.colegio_id,
        st.grade_id,
        g.name AS grade_name,
        st.section_id,
        se.name AS section_name,
        COUNT(*) AS active_student_count
    FROM educheck_students st
    INNER JOIN educheck_grades g
        ON g.id = st.grade_id AND g.colegio_id = st.colegio_id
    INNER JOIN educheck_sections se
        ON se.id = st.section_id AND se.colegio_id = st.colegio_id
    WHERE st.active = 1
    GROUP BY st.colegio_id, st.grade_id, g.name, st.section_id, se.name
    """,
    """
    CREATE OR REPLACE VIEW vw_educheck_attendance_summary AS
    SELECT
        ar.colegio_id,
        ar.`date`,
        ar.shift,
        st.grade_id,
        g.name AS grade_name,
        st.section_id,
        se.name AS section_name,
        COUNT(DISTINCT ar.student_id) AS present_count
    FROM educheck_attendance ar
    INNER JOIN educheck_students st
        ON st.id = ar.student_id AND st.colegio_id = ar.colegio_id
    INNER JOIN educheck_grades g
        ON g.id = st.grade_id AND g.colegio_id = ar.colegio_id
    INNER JOIN educheck_sections se
        ON se.id = st.section_id AND se.colegio_id = ar.colegio_id
    GROUP BY
        ar.colegio_id, ar.date, ar.shift,
        st.grade_id, g.name, st.section_id, se.name
    """,
)

TRIGGER_NAMES = (
    "educheck_section_school_bi",
    "educheck_section_school_bu",
    "educheck_student_school_bi",
    "educheck_student_school_bu",
    "educheck_attendance_school_bi",
    "educheck_attendance_school_bu",
)
VIEW_NAMES = (
    "vw_educheck_students_by_section",
    "vw_educheck_attendance_summary",
)


def create_mariadb_objects(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    with schema_editor.connection.cursor() as cursor:
        for statement in TRIGGERS + VIEWS:
            cursor.execute(statement)


def drop_mariadb_objects(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    with schema_editor.connection.cursor() as cursor:
        for view_name in VIEW_NAMES:
            cursor.execute(f"DROP VIEW IF EXISTS `{view_name}`")
        for trigger_name in TRIGGER_NAMES:
            cursor.execute(f"DROP TRIGGER IF EXISTS `{trigger_name}`")


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.RunPython(create_mariadb_objects, drop_mariadb_objects),
    ]
