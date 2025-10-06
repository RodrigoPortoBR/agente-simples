-- ================================
-- SCHEMA PARA MEMÓRIA DE AGENTES
-- ================================

-- Tabela de sessões de conversa
CREATE TABLE IF NOT EXISTS agent_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Índices para performance
    CONSTRAINT agent_conversations_session_id_key UNIQUE (session_id)
);

-- Tabela de mensagens
CREATE TABLE IF NOT EXISTS agent_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Foreign key
    CONSTRAINT fk_session
        FOREIGN KEY (session_id)
        REFERENCES agent_conversations(session_id)
        ON DELETE CASCADE
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_messages_session_id ON agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON agent_messages(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_messages_session_timestamp ON agent_messages(session_id, timestamp DESC);

-- Função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para atualizar updated_at
DROP TRIGGER IF EXISTS update_agent_conversations_updated_at ON agent_conversations;
CREATE TRIGGER update_agent_conversations_updated_at
    BEFORE UPDATE ON agent_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comentários
COMMENT ON TABLE agent_conversations IS 'Sessões de conversa com agentes';
COMMENT ON TABLE agent_messages IS 'Mensagens individuais das conversas';
COMMENT ON COLUMN agent_messages.role IS 'Papel: user, assistant ou system';
COMMENT ON COLUMN agent_messages.metadata IS 'Metadados adicionais (agents_used, intent_type, etc)';

-- ================================
-- POLÍTICAS RLS (Row Level Security)
-- ================================

-- Habilitar RLS
ALTER TABLE agent_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;

-- Política: permitir todas operações (ajuste conforme necessidade de segurança)
CREATE POLICY "Enable all access for agent_conversations" ON agent_conversations
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Enable all access for agent_messages" ON agent_messages
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- ================================
-- FUNÇÕES AUXILIARES
-- ================================

-- Função para limpar mensagens antigas (manutenção)
CREATE OR REPLACE FUNCTION cleanup_old_messages(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM agent_messages
    WHERE timestamp < NOW() - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Função para obter estatísticas de uma sessão
CREATE OR REPLACE FUNCTION get_session_stats(p_session_id TEXT)
RETURNS TABLE (
    session_id TEXT,
    message_count BIGINT,
    first_message TIMESTAMP WITH TIME ZONE,
    last_message TIMESTAMP WITH TIME ZONE,
    user_messages BIGINT,
    assistant_messages BIGINT
) AS $
BEGIN
    RETURN QUERY
    SELECT 
        p_session_id,
        COUNT(*)::BIGINT,
        MIN(timestamp),
        MAX(timestamp),
        COUNT(*) FILTER (WHERE role = 'user')::BIGINT,
        COUNT(*) FILTER (WHERE role = 'assistant')::BIGINT
    FROM agent_messages
    WHERE agent_messages.session_id = p_session_id;
END;
$ LANGUAGE plpgsql;

-- ================================
-- DADOS DE EXEMPLO (OPCIONAL)
-- ================================

-- Inserir sessão de exemplo (comentado - descomentar se quiser testar)
-- INSERT INTO agent_conversations (session_id, metadata) 
-- VALUES ('test_session_001', '{"source": "test"}');

-- INSERT INTO agent_messages (session_id, role, content, metadata)
-- VALUES 
--     ('test_session_001', 'user', 'Olá!', '{}'),
--     ('test_session_001', 'assistant', 'Olá! Como posso ajudar?', '{"intent_type": "general_chat"}');

-- ================================
-- QUERIES ÚTEIS
-- ================================

-- Ver todas as sessões ativas
-- SELECT session_id, created_at, updated_at, 
--        (SELECT COUNT(*) FROM agent_messages WHERE agent_messages.session_id = agent_conversations.session_id) as msg_count
-- FROM agent_conversations
-- ORDER BY updated_at DESC;

-- Ver mensagens de uma sessão
-- SELECT role, content, timestamp 
-- FROM agent_messages 
-- WHERE session_id = 'sua_session_id'
-- ORDER BY timestamp ASC;

-- Estatísticas de uma sessão
-- SELECT * FROM get_session_stats('sua_session_id');