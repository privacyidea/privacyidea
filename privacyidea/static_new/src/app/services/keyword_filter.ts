export class KeywordFilter {
  keyword: string;
  label: string;
  isSelected: (value: string) => boolean;

  /// Allowed return values: 'remove_circle' | 'add_circle' | change_circle
  getIconName: (value: string) => string;
  toggleKeyword: (filterValue: string) => string;
  constructor(named: {
    key: string;
    label: string;
    isSelected?: (filterValue: string) => boolean;
    iconName?: (value: string) => string;
    toggle?: (filterValue: string) => string;
  }) {
    this.keyword = named.key;
    this.label = named.label;
    this.isSelected =
      named.isSelected ??
      ((filterValue: string) =>
        KeywordFilter.defaultIsSelected({
          keyword: this.keyword,
          filterValue: filterValue,
        }));
    this.getIconName =
      named.iconName ??
      ((filterValue: string) =>
        KeywordFilter.defaultIconName({
          isSelected: this.isSelected,
          keyword: this.keyword,
          filterValue: filterValue,
        }));
    this.toggleKeyword =
      named.toggle ??
      ((filterValue: string) =>
        KeywordFilter.defaultToggler({
          keyword: this.keyword,
          filterValue: filterValue,
        }));
  }
  static defaultIsSelected(named: { keyword: string; filterValue: string }) {
    const { keyword, filterValue } = named;
    const regex = new RegExp(`\\b${keyword}:`, 'i');
    return regex.test(filterValue);
  }

  static defaultIconName(named: {
    isSelected?: (filterValue: string) => boolean;
    keyword: string;
    filterValue: string;
  }) {
    const { isSelected, keyword, filterValue } = named;
    const filterIsSelected = isSelected
      ? isSelected(filterValue)
      : KeywordFilter.defaultIsSelected({
          keyword: keyword,
          filterValue: filterValue,
        });
    return filterIsSelected ? 'remove_circle' : 'add_circle';
  }

  static defaultToggler(named: {
    keyword: string;
    filterValue: string;
  }): string {
    const { keyword, filterValue } = named;
    const keywordPattern = new RegExp(
      `\\b${keyword}:.*?(?=(\\s+\\w+:|$))`,
      'i',
    );
    if (keywordPattern.test(filterValue)) {
      return filterValue
        .replace(keywordPattern, '')
        .trim()
        .replace(/\s{2,}/g, ' ');
    } else {
      if (filterValue.length > 0) {
        return (filterValue + ` ${keyword}: `).replace(/\s{2,}/g, ' ');
      } else {
        return `${keyword}: `;
      }
    }
  }

  static getValue(named: {
    keyword: string;
    filterValue: string;
  }): string | null {
    const { keyword, filterValue } = named;
    const keywordPattern = new RegExp(
      `(?<=${keyword}:)\\s*[\\w\\d]*(?=\\s|$)`,
      'i',
    );
    const match = filterValue.match(keywordPattern);
    if (match) {
      return match[0].trim();
    } else {
      return null;
    }
  }

  static toggleActive(filterValue: string): string {
    const activeRegex = /active:\s*(\S+)/i;
    const match = filterValue.match(activeRegex);

    if (!match) {
      return (filterValue.trim() + ' active: true').trim();
    } else {
      const existingValue = match[1].toLowerCase();

      if (existingValue === 'true') {
        return filterValue.replace(activeRegex, 'active: false');
      } else if (existingValue === 'false') {
        const removed = filterValue.replace(activeRegex, '').trim();
        return removed.replace(/\s{2,}/g, ' ');
      } else {
        return filterValue.replace(activeRegex, 'active: true');
      }
    }
  }
}
