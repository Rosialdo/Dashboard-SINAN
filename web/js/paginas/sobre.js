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
      <dt>Incidência</dt><dd>Casos ÷ população × 100 mil. Com vários anos, é a média anual (casos ÷ soma da população de cada ano). A incidência não aparece com filtro de sexo ou faixa etária, nem na contagem pelo município de notificação, porque a população não corresponde aos casos.</dd>
      <dt>Incidência suavizada</dt><dd>Incidência de cada município aproximada da média da área, tanto mais quanto menor a população (método bayesiano empírico global de Marshall). Serve para comparar municípios pequenos, em que poucos casos mudam muito a taxa. Como usa a média da área, um município realmente diferente dos outros também é puxado para ela: para boletins, alertas e para dizer se há surto, use a incidência. Não aparece com um município escolhido, com filtro de sexo ou faixa etária, nem na contagem pelo município de notificação, porque nesses casos a população não corresponde aos casos.</dd>
      <dt>Faixa histórica (canal endêmico)</dt><dd>A faixa cinza atrás da curva por semana mostra o que costuma acontecer em cada semana. Ela é a metade do meio dos anos anteriores: em cada semana, cerca de 1 em cada 4 anos ficou abaixo da faixa e cerca de 1 em cada 4 ficou acima. A linha tracejada é a mediana (o valor do meio). Olha os 7 anos anteriores; entram só os anos completos já baixados. Um ano só conta se os arquivos dele e do ano seguinte estiverem baixados, porque parte dos casos é notificada em janeiro. Anos com muito mais casos que o normal (mais de 1,5 vez a mediana dos totais anuais) ficam de fora, e é preciso sobrar ao menos 5 anos. A semana 53 usa a faixa da semana 52. Cada área e cada município decidem os próprios anos fora. A faixa segue a contagem escolhida (confirmados, prováveis ou notificações) e, com vários anos no filtro, é calculada para o último ano. A curva por semana mostra o último ano do período contra a faixa; marque “Mostrar anos anteriores” para pôr de volta as linhas dos outros anos. Este método é provisório, até a validação pela vigilância; a faixa é um sinal para investigar, não prova de epidemia.</dd>
      <dt>Não informado</dt><dd>A pergunta ficou em branco na ficha de notificação ou foi marcada como “ignorado” (no TabNet aparece como “Ign/Branco”). Muitos casos assim indicam ficha incompleta, não ausência da característica.</dd>
      <dt>Em aberto</dt><dd>Caso que ainda não recebeu classificação final (confirmado ou descartado), em geral porque a investigação não terminou.</dd>
      <dt>Prazos (tela Qualidade dos dados)</dt><dd>Notificação: até 7 dias entre os primeiros sintomas e a notificação. Digitação: até 7 dias entre a notificação e o lançamento no sistema. Investigação: até 2 dias entre a notificação e a investigação; fora das doenças de notificação imediata, esse valor é uma referência provisória, ainda não validada pela vigilância. Encerramento: até 60 dias entre a notificação e o encerramento. O percentual usa só as fichas avaliáveis, isto é, com as duas datas preenchidas e válidas; datas ausentes, ilegíveis ou trocadas ficam fora. No encerramento, as fichas sem data de encerramento registrada há mais de 60 dias contam como fora do prazo (isso não é o mesmo que “Em aberto”, que é a classificação final vazia). “Há mais de 60 dias” é contado até a data do arquivo do DATASUS, mostrada na tela. Anos cujos arquivos não trazem a data de encerramento ficam fora dessa conta.</dd>
      <dt>Residência × notificação</dt><dd>Por padrão os casos são contados no município onde a pessoa mora.</dd>
      <dt>Alerta da semana (mapa e tabela)</dt><dd>No mapa, “Alerta da semana” compara, em cada município, os casos da última semana epidemiológica considerada com a faixa histórica do próprio município. Essa semana é a que contém o dia de 7 dias antes da data dos dados; ela já terminou no calendário, mas pode estar incompleta por atraso de notificação, então “abaixo” não quer dizer melhora. “Acima da faixa histórica” significa mais casos que o limite de cima da faixa; “abaixo”, menos que o limite de baixo. Quando o limite de cima é zero (poucos casos), basta 1 caso para ficar “acima”, e a tela avisa “faixa histórica zero: poucos casos, confira”. É um sinal para investigar, não a declaração de uma epidemia. Aqui contam as notificações não descartadas, qualquer que seja a contagem escolhida no filtro, porque na semana recente quase toda ficha ainda está em aberto. Sem histórico suficiente, ou com a semana ainda não baixada para a sua UF, o município aparece listrado e sem nível. No site publicado, o número de casos da semana por município não é mostrado, para proteger a privacidade; aparece só o nível.</dd>
    </dl>
    <h2 style="margin-top:22px">Cuidados na interpretação</h2>
    <ul>
      <li>Os anos mais recentes são <b>preliminares</b> e mudam a cada atualização do DATASUS.</li>
      <li>As últimas semanas sempre parecem menores por causa do atraso entre o início dos sintomas e o registro.</li>
      <li>Municípios pequenos têm incidências instáveis: poucos casos mudam muito a taxa. Para compará-los, use a incidência suavizada no mapa.</li>
      <li>Os arquivos de dengue do DATASUS não trazem os casos descartados.</li>
      <li>Na Amazônia Legal, a malária é notificada no SIVEP-Malária, não no SINAN.</li>
      <li>A síndrome respiratória aguda grave (SRAG) vem do SIVEP-Gripe (OpenDataSUS), não do SINAN. Inclui só casos internados ou óbitos, e os anos mais recentes mudam toda semana. Casos sem classificação aparecem como "Em investigação". Disponível apenas no painel instalado no computador.</li>
      <li>Na SRAG de 2026, os boletins do SIVEP-Gripe numeram as semanas epidemiológicas uma à frente do SINAN. O painel usa a mesma regra do SINAN para todas as doenças.</li>
      <li>Para conferir números, compare com o TabNet: <a href="http://tabnet.datasus.gov.br" target="_blank" rel="noopener">tabnet.datasus.gov.br</a>.</li>
    </ul>
  </section>`);
}
