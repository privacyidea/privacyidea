export class FilterValue {
  private _value: string;
  get value(): string {
    return this._value;
  }

  private _hiddenValue: string;
  get hiddenValue(): string {
    return this._hiddenValue;
  }

  get isEmpty(): boolean {
    return this._value.length === 0;
  }
  get isNotEmpty(): boolean {
    return this._value.length > 0;
  }
  get filterString(): string {
    return this._value;
  }
  set setString(newValue: string) {
    this._value = this._normalize(newValue);
  }

  constructor(args: { value?: string; hiddenValue?: string } = {}) {
    this._value = args.value ? this._normalize(args.value) : "";
    this._hiddenValue = args.hiddenValue ? this._normalize(args.hiddenValue) : "";
  }

  public copyWith(args?: { value?: string; hiddenValue?: string }): FilterValue {
    const newFilter = new FilterValue({
      value: args?.value ?? this._value,
      hiddenValue: args?.hiddenValue ?? this._hiddenValue
    });
    return newFilter;
  }

  public addKey(key: string): FilterValue {
    // Adds a new key to the string if it does not already exist.
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    if (!this._value.match(regex)) {
      this._value = this._value ? `${this._value} ${key}: ` : `${key}: `;
    }
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }
  public addHiddenKey(key: string): FilterValue {
    // Adds a new key to the string if it does not already exist.
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    if (!this._hiddenValue.match(regex)) {
      this._hiddenValue = this._hiddenValue ? `${this._hiddenValue} ${key}: ` : `${key}: `;
    }
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }
  public getValueOfKey(key: string): string | undefined {
    return this.filterMap.get(key);
  }

  public removeKey(key: string): FilterValue {
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    this._value = this._value.replace(regex, "").trim().replace(/\s+/g, " ");
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public removeHiddenKey(key: string): FilterValue {
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    this._hiddenValue = this._hiddenValue.replace(regex, "").trim().replace(/\s+/g, " ");
    return new FilterValue({ value: this._value, hiddenValue: this._hiddenValue });
  }

  public hasKey(key: string): boolean {
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    return regex.test(this._value);
  }

  public toggleKey(key: string): FilterValue {
    if (this.hasKey(key)) {
      return this.removeKey(key);
    } else {
      return this.addKey(key);
    }
  }

  get filterMap(): Map<string, string> {
    // Convert the normalized string back to a map.
    // Each key-value pair is separated by space. Key and value are separated by colon followed by a space.
    // Example:
    // "key1: value1 value2 key2: key3: value3 ..." => {key1:value1,key2:,key3:value3,...}
    // Incorrect formats are ignored.

    const map = new Map<string, string>();
    const regex = RegExp(/(?<=^|\s)[\w\d]+:\s*[\w\d]*(?=$|\s)/, "g");
    const matches = this._value.match(regex);
    if (matches) {
      matches.forEach((pair) => {
        let [key, value] = pair.split(/:/); // Split only on the first occurrence of ": "
        value = value?.trim();
        if (key) {
          map.set(key, value ?? "");
        }
      });
    }
    return map;
  }

  get hiddenFilterMap(): Map<string, string> {
    // Convert the normalized string back to a map.
    // Each key-value pair is separated by space. Key and value are separated by colon followed by a space.
    // Example:
    // "key1: value1 value2 key2: key3: value3 ..." => {key1:value1,key2:,key3:value3,...}
    // Incorrect formats are ignored.

    const map = new Map<string, string>();
    const regex = RegExp(/(?<=^|\s)[\w\d]+:\s*[\w\d]*(?=$|\s)/, "g");
    const matches = this._hiddenValue.match(regex);
    if (matches) {
      matches.forEach((pair) => {
        let [key, value] = pair.split(/:/); // Split only on the first occurrence of ": "
        value = value?.trim();
        if (key) {
          map.set(key, value ?? "");
        }
      });
    }
    return map;
  }

  public addEntry(key: string, value: string): void {
    const map = this.filterMap;
    map.set(key, value);
    this.setFromMap(map);
  }

  /**
   * Sets the filter value from a map of key-value pairs.
   * Converts the map to the normalized string format and updates _value.
   */
  public setFromMap(map: Map<string, string>): void {
    // Convert the map to the normalized string format: "key1: value1 key2: value2 ..."
    const entries: string[] = [];
    map.forEach((value, key) => {
      entries.push(`${key}: ${value}`);
    });
    this._value = entries.join(" ");
  }

  private _normalize(value: string): string {
    return value.toLowerCase();
  }
}
