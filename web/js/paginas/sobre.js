/* Tela "Sobre os dados": fonte, definições e cuidados de interpretação. */

export function montar(raiz) {
  raiz.insertAdjacentHTML("beforeend", `
  <section class="card card-corpo texto" style="margin-bottom:14px;max-width:none">
    <h2>Fonte</h2>
    <p>Sistema de Informação de Agravos de Notificação (SINAN): microdados públicos e anonimizados do DATASUS/Ministério da Saúde
      (<code>ftp.datasus.gov.br/dissemin/publicos/SINAN</code>). População: IBGE (estimativas anuais e Censo 2022).
      Rótulos das variáveis: arquivos oficiais do tabulador TabNet. Mapa: malha municipal do IBGE.</p>
    <h2 style="margin-top:22px">Como os números são calculados</h2>
    <dl>
      <dt>Ano</dt><dd>Ano da notificação (igual ao arquivo do DATASUS e ao padrão do TabNet).</dd>
      <dt>Semana epidemiológica</dt><dd>Semana (domingo a sábado) do início dos sintomas; sem essa data, usa o diagnóstico ou a notificação. A semana 1 é a primeira com ao menos 4 dias no ano.</dd>
      <dt>Confirmado</dt><dd>Classificação final do caso. Dengue: dengue, com sinais de alarme e grave (e as classificações antigas antes de 2014). Chikungunya: código 13. Demais: rótulo “confirmado” da ficha. Em tuberculose, hanseníase, violência e acidentes de trabalho, toda notificação é um caso.</dd>
      <dt>Provável</dt><dd>Todas as notificações exceto as descartadas, medida usada nos boletins de arboviroses.</dd>
      <dt>Óbito</dt><dd>Evolução “óbito pelo agravo” (não conta óbito por outras causas nem em investigação).</dd>
      <dt>Letalidade</dt><dd>Óbitos pelo agravo ÷ casos confirmados × 100.</dd>
      <dt>Incidência</dt><dd>Casos ÷ população × 100 mil. Com vários anos, é a média anual (casos ÷ soma da população de cada ano).</dd>
      <dt>Não informado</dt><dd>A pergunta ficou em branco na ficha de notificação ou foi marcada como “ignorado” (no TabNet aparece como “Ign/Branco”). Muitos casos assim indicam ficha incompleta, não ausência da característica.</dd>
      <dt>Em aberto</dt><dd>Caso que ainda não recebeu classificação final (confirmado ou descartado), em geral porque a investigação não terminou.</dd>
      <dt>Residência × notificação</dt><dd>Por padrão os casos são contados no município onde a pessoa mora.</dd>
    </dl>
    <h2 style="margin-top:22px">Cuidados na interpretação</h2>
    <ul>
      <li>Os anos mais recentes são <b>preliminares</b> e mudam a cada atualização do DATASUS.</li>
      <li>As últimas semanas sempre parecem menores por causa do atraso entre o início dos sintomas e o registro.</li>
      <li>Municípios pequenos têm incidências instáveis: poucos casos mudam muito a taxa.</li>
      <li>Os arquivos de dengue do DATASUS não trazem os casos descartados.</li>
      <li>Na Amazônia Legal, a malária é notificada no SIVEP-Malária, não no SINAN.</li>
      <li>Para conferir números, compare com o TabNet: <a href="http://tabnet.datasus.gov.br" target="_blank" rel="noopener">tabnet.datasus.gov.br</a>.</li>
    </ul>
  </section>`);
}
