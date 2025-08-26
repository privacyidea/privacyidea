export class FilterValue {
  private _value: string;
  private _hiddenValue: string;

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
  set setMap(newValue: Map<string, string>) {
    // Convert map to a normalized string representation
    // {key1:value1,key2:value2,...} => "key1: value1 key2: value2 ..."
    this._value = Array.from(newValue.entries())
      .map(([key, value]) => `${key}: ${value}`)
      .join(" ");
  }

  constructor(args: { value?: string; hiddenValue?: string } = {}) {
    this._value = args.value ? this._normalize(args.value) : "";
    this._hiddenValue = args.hiddenValue ? this._normalize(args.hiddenValue) : "";
  }

  public copyWith(args?: { value?: string; hiddenValue?: string }): FilterValue {
    return new FilterValue({ value: args?.value ?? this._value, hiddenValue: args?.hiddenValue ?? this._hiddenValue });
  }

  public addKey(key: string): void {
    // Adds a new key to the string if it does not already exist.
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    if (!this._value.match(regex)) {
      this._value = this._value ? `${this._value} ${key}: ` : `${key}: `;
    }
  }
  public addHiddenKey(key: string) {
    // Adds a new key to the string if it does not already exist.
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    if (!this._hiddenValue.match(regex)) {
      this._hiddenValue = this._hiddenValue ? `${this._hiddenValue} ${key}: ` : `${key}: `;
    }
  }
  public getValue(keyword: string): string | undefined {
    return this.filterMap.get(keyword);
  }

  public removeKey(key: string): void {
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    this._value = this._value.replace(regex, "").trim().replace(/\s+/g, "");
  }

  public removeHiddenKey(key: string) {
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    this._hiddenValue = this._hiddenValue.replace(regex, "").trim().replace(/\s+/g, "");
  }

  public hasKey(key: string): boolean {
    const regex = new RegExp(`(?<=^|\\s)(${key})+:\\s*[\\w\\d]*(?=$|\\s)`, "g");
    return regex.test(this._value);
  }

  public toggleKey(key: string): void {
    if (this.hasKey(key)) {
      this.removeKey(key);
    } else {
      this.addKey(key);
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
    console.log(this._value, matches);
    if (matches) {
      matches.forEach((pair) => {
        const [key, value] = pair.split(/:\s+(.+)/); // Split only on the first occurrence of ": "
        if (key && value) {
          map.set(key, value);
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
        const [key, value] = pair.split(/:\s+(.+)/); // Split only on the first occurrence of ": "
        if (key && value) {
          map.set(key, value);
        }
      });
    }
    return map;
  }

  public addEntry(key: string, value: string): void {
    const map = this.filterMap;
    map.set(key, value);
    this.setMap = map;
  }

  private _normalize(value: string): string {
    return value.toLowerCase();
  }
}
