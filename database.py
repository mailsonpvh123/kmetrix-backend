-- 1. Tabela de Motoristas (Usuários/Autenticação)
-- Gerencia o acesso ao KMetrix através da X-API-Key.
CREATE TABLE drivers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Perfil Financeiro (Entrevista de Custos)
-- Armazena os parâmetros matemáticos inegociáveis para o cálculo de lucro real.
CREATE TABLE financial_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID REFERENCES drivers(id) ON DELETE CASCADE,
    rent_cost NUMERIC(10, 2) DEFAULT 0.00,
    insurance_cost NUMERIC(10, 2) DEFAULT 0.00,
    other_fixed_costs NUMERIC(10, 2) DEFAULT 0.00,
    fuel_cost_per_liter NUMERIC(10, 2) DEFAULT 0.00,
    vehicle_consumption NUMERIC(10, 2) DEFAULT 0.00, -- km/l
    target_per_km NUMERIC(10, 2) DEFAULT 0.00,
    target_per_hour NUMERIC(10, 2) DEFAULT 0.00,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(driver_id)
);

-- 3. Gestão de Turnos (Sessões de Trabalho)
-- O coração do rastreamento. Controla o tempo logado e acumula as métricas de km.
CREATE TABLE shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_id UUID REFERENCES drivers(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL, -- Estados: 'ACTIVE', 'PAUSED', 'ENDED'
    start_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP WITH TIME ZONE,
    total_km NUMERIC(10, 2) DEFAULT 0.00,
    paid_km NUMERIC(10, 2) DEFAULT 0.00,
    empty_km NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Eventos e Logs do Turno (GPS e Estados)
-- Registra a "linha do tempo" do turno. Essencial para separar km vazio de km pago e auditar pausas.
CREATE TABLE shift_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shift_id UUID REFERENCES shifts(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, -- Ex: 'START', 'PAUSE', 'RESUME', 'GPS_TICK', 'END'
    latitude DECIMAL(9,6),  -- Precisão de até ~11cm
    longitude DECIMAL(9,6),
    is_paid_route BOOLEAN DEFAULT FALSE, -- Flag acionada quando o app identifica uma corrida em andamento
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Registro de Corridas e Histórico
-- Recebe os dados brutos lidos da tela pela automação do app.
CREATE TABLE rides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shift_id UUID REFERENCES shifts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL, -- Ex: 'Uber', '99', 'inDrive'
    profit NUMERIC(10, 2) NOT NULL, -- Valor financeiro extraído
    distance_km NUMERIC(10, 2),
    duration_minutes INTEGER,
    alerts JSONB, -- Estrutura flexível para salvar os alertas (ex: {"area_risco": true, "nota_baixa": false})
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
