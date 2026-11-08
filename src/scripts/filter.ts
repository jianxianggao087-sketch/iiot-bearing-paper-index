const form = document.querySelector<HTMLFormElement>('#filter-bar');
const yearSelect = document.querySelector<HTMLSelectElement>('#filter-year');
const journalSelect = document.querySelector<HTMLSelectElement>('#filter-journal');
const queryInput = document.querySelector<HTMLInputElement>('#filter-query');
const sortSelect = document.querySelector<HTMLSelectElement>('#sort-by');
const list = document.querySelector<HTMLDivElement>('#paper-list');
const count = document.querySelector<HTMLParagraphElement>('#result-count');
const emptyState = document.querySelector<HTMLParagraphElement>('#empty-state');
const loadMore = document.querySelector<HTMLButtonElement>('#load-more');

if (form && yearSelect && journalSelect && queryInput && sortSelect && list && count && emptyState && loadMore) {
  const cards = Array.from(list.querySelectorAll<HTMLElement>('.paper-card'));
  const pageSize = 30;
  let visibleLimit = pageSize;
  let debounceTimer = 0;

  const params = new URLSearchParams(window.location.search);
  yearSelect.value = params.get('year') || 'all';
  journalSelect.value = params.get('journal') || 'all';
  queryInput.value = params.get('q') || '';
  sortSelect.value = params.get('sort') || 'latest';

  const updateUrl = () => {
    const url = new URL(window.location.href);
    const values: Record<string, string> = {
      year: yearSelect.value,
      journal: journalSelect.value,
      q: queryInput.value.trim(),
      sort: sortSelect.value,
    };
    for (const [key, value] of Object.entries(values)) {
      if (!value || value === 'all' || (key === 'sort' && value === 'latest')) url.searchParams.delete(key);
      else url.searchParams.set(key, value);
    }
    window.history.replaceState(null, '', `${url.pathname}${url.search}${url.hash}`);
  };

  const render = (resetLimit = true) => {
    if (resetLimit) visibleLimit = pageSize;
    const query = queryInput.value.trim().toLocaleLowerCase();
    const matches = cards.filter((card) => {
      const matchesYear = yearSelect.value === 'all' || card.dataset.year === yearSelect.value;
      const matchesJournal = journalSelect.value === 'all' || card.dataset.journal === journalSelect.value;
      const matchesQuery = !query || (card.dataset.search || '').includes(query);
      return matchesYear && matchesJournal && matchesQuery;
    });

    matches.sort((left, right) => {
      const leftDate = left.dataset.date || '';
      const rightDate = right.dataset.date || '';
      const leftCited = Number(left.dataset.cited || 0);
      const rightCited = Number(right.dataset.cited || 0);
      return sortSelect.value === 'cited'
        ? rightCited - leftCited || rightDate.localeCompare(leftDate)
        : rightDate.localeCompare(leftDate) || rightCited - leftCited;
    });

    const visibleSet = new Set(matches.slice(0, visibleLimit));
    for (const card of cards) card.hidden = !visibleSet.has(card);
    for (const card of matches) list.append(card);

    const shown = Math.min(matches.length, visibleLimit);
    count.textContent = `显示 ${shown} / 共 ${matches.length} 篇`;
    emptyState.hidden = matches.length > 0;
    list.hidden = matches.length === 0;
    loadMore.hidden = matches.length <= visibleLimit;
    updateUrl();
  };

  yearSelect.addEventListener('change', () => render());
  journalSelect.addEventListener('change', () => render());
  sortSelect.addEventListener('change', () => render());
  queryInput.addEventListener('input', () => {
    window.clearTimeout(debounceTimer);
    debounceTimer = window.setTimeout(() => render(), 300);
  });
  loadMore.addEventListener('click', () => {
    visibleLimit += pageSize;
    render(false);
  });
  form.addEventListener('reset', () => {
    window.setTimeout(() => render(), 0);
  });
  render(false);
}
