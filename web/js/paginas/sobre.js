/* Tela "Sobre os dados": fonte, definições e cuidados de interpretação. */

import { estado } from "../nucleo/estado.js";

/** Só no site publicado (decisão de 19/11/2026). */
const PRIVACIDADE = `
  <section class="card card-corpo texto" style="margin-bottom:14px;max-width:none">
    <h2>Sobre este painel e privacidade</h2>
    <p>Este é um projeto de estudo do grupo PRISM. Ele mostra apenas números agregados, calculados a partir dos dados
      públicos do SINAN disponibilizados pelo Ministério da Saúde (DATASUS). Os dados do ano corrente são preliminares, e
      este painel não substitui as fontes oficiais.</p>
    <p>Nenhuma ficha individual é publicada. Para evitar a identificação de pessoas, gestação, evolução do caso (óbito),
      hospitalização e doença relacionada ao trabalho não aparecem quando um município está selecionado.</p>
    <p>O site não usa cookies e não coleta dados de quem o visita: o servidor não guarda registro de acesso nem o
      endereço IP. O tema e os filtros escolhidos ficam guardados só no seu navegador.</p>
  </section>`;

export function montar(raiz) {
  if (estado.meta?.publico) raiz.insertAdjacentHTML("beforeend", PRIVACIDADE);
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
      <dt>Prazos (tela Qualidade dos dados)</dt><dd>Notificação: até 7 dias entre os primeiros sintomas e a notificação. Digitação: até 7 dias entre a notificação e o lançamento no sistema. Investigação: até 2 dias entre a notificação e a investigação; fora das doenças de notificação imediata, esse valor é uma referência provisória, ainda não validada pela vigilância. Encerramento: até 60 dias entre a notificação e o encerramento. O percentual usa só as fichas avaliáveis, isto é, com as duas datas preenchidas e válidas; datas ausentes, ilegíveis ou trocadas ficam fora. No encerramento, as fichas sem data de encerramento registrada há mais de 60 dias contam como fora do prazo (isso não é o mesmo que “Em aberto”, que é a classificação final vazia). “Há mais de 60 dias” é contado até a data do arquivo do DATASUS, mostrada na tela. Anos cujos arquivos não trazem a data de encerramento ficam fora dessa conta.</dd>
      <dt>Residência × notificação</dt><dd>Por padrão os casos são contados no município onde a pessoa mora.</dd>
    </dl>
    <h2 style="margin-top:22px">Cuidados na interpretação</h2>
    <ul>
      <li>Os anos mais recentes são <b>preliminares</b> e mudam a cada atualização do DATASUS.</li>
      <li>As últimas semanas sempre parecem menores por causa do atraso entre o início dos sintomas e o registro.</li>
      <li>Municípios pequenos têm incidências instáveis: poucos casos mudam muito a taxa.</li>
      <li>Os arquivos de dengue do DATASUS não trazem os casos descartados.</li>
      <li>Na Amazônia Legal, a malária é notificada no SIVEP-Malária, não no SINAN.</li>
      <li>A síndrome respiratória aguda grave (SRAG) vem do SIVEP-Gripe (OpenDataSUS), não do SINAN. Inclui só casos internados ou óbitos, e os anos mais recentes mudam toda semana. Casos sem classificação aparecem como "Em investigação". Disponível apenas no painel instalado no computador.</li>
      <li>Na SRAG de 2026, os boletins do SIVEP-Gripe numeram as semanas epidemiológicas uma à frente do SINAN. O painel usa a mesma regra do SINAN para todas as doenças.</li>
      <li>Para conferir números, compare com o TabNet: <a href="http://tabnet.datasus.gov.br" target="_blank" rel="noopener">tabnet.datasus.gov.br</a>.</li>
    </ul>
  </section>`);
}
