import { FilterValue } from "./filter_value";

describe("FilterValue parsing", () => {
  test("parses dots in values (no truncation at .)", () => {
    const fv = new FilterValue({ value: "description: v1.2" });
    expect(fv.filterMap.get("description")).toBe("v1.2");
  });

  test("captures multi-word unquoted value up to the next key", () => {
    const fv = new FilterValue({ value: "description: this token is user: alice" });
    expect(fv.filterMap.get("description")).toBe("this token is");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("supports double-quoted phrases", () => {
    const fv = new FilterValue({ value: `description:"this token was created remotely" user:alice` });
    expect(fv.filterMap.get("description")).toBe("this token was created remotely");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("supports single-quoted phrases", () => {
    const fv = new FilterValue({ value: `description:'this token is unused' user:alice` });
    expect(fv.filterMap.get("description")).toBe("this token is unused");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("does not swallow the next key when previous value is empty (serial: description: test)", () => {
    const fv = new FilterValue({ value: "serial: description: test" });
    expect(fv.filterMap.get("serial")).toBe("");
    expect(fv.filterMap.get("description")).toBe("test");
  });

  test("allows empty values explicitly (serial:)", () => {
    const fv = new FilterValue({ value: "serial:" });
    expect(fv.filterMap.get("serial")).toBe("");
  });

  test("multiple pairs with punctuation and spaces", () => {
    const fv = new FilterValue({
      value: `description:"v1.2 release - final" user: bob@example.com realm:"engineering team"`
    });
    expect(fv.filterMap.get("description")).toBe("v1.2 release - final");
    expect(fv.filterMap.get("user")).toBe("bob@example.com");
    expect(fv.filterMap.get("realm")).toBe("engineering team");
  });

  test("hiddenFilterMap mirrors parsing rules", () => {
    const fv = new FilterValue({ hiddenValue: `serial: ABC.123 description:"hidden stuff"` });
    expect(fv.hiddenFilterMap.get("serial")).toBe("ABC.123");
    expect(fv.hiddenFilterMap.get("description")).toBe("hidden stuff");
  });
});

describe("FilterValue helpers", () => {
  test("addKey inserts key once and hasKey detects it", () => {
    let fv = new FilterValue();
    fv = fv.addKey("serial");
    expect(fv.value).toBe("serial: ");
    fv = fv.addKey("serial");
    expect(fv.value).toBe("serial: ");
    expect(fv.hasKey("serial")).toBe(true);
  });

  test("removeKey removes the whole segment of that key only", () => {
    let fv = new FilterValue({ value: `serial: description:"this token is" user: alice` });
    fv = fv.removeKey("description");
    expect(fv.filterMap.get("description")).toBeUndefined();
    expect(fv.filterMap.get("serial")).toBe("");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("addHiddenKey / removeHiddenKey behave like visible counterparts", () => {
    let fv = new FilterValue({ hiddenValue: "" });
    fv = fv.addHiddenKey("container_serial");
    expect(fv.hiddenFilterMap.get("container_serial")).toBe("");
    fv = fv.removeHiddenKey("container_serial");
    expect(fv.hiddenFilterMap.get("container_serial")).toBeUndefined();
  });

  test("addEntry updates value for a key", () => {
    let fv = new FilterValue({ value: "description:" });
    fv = fv.addEntry("description", "this token is");
    expect(fv.filterMap.get("description")).toBe("this token is");
  });
});

describe("Round-trip safety via setFromMap", () => {
  test("map -> setFromMap -> parse yields the same key/values (handles spaces and dots)", () => {
    const source = new Map<string, string>([
      ["description", "this token is unused"],
      ["user", "bob@example.com"],
      ["version", "v1.2.3"]
    ]);

    const fv = new FilterValue();
    fv.setFromMap(source);

    const parsed = fv.filterMap;
    expect(parsed.get("description")).toBe("this token is unused");
    expect(parsed.get("user")).toBe("bob@example.com");
    expect(parsed.get("version")).toBe("v1.2.3");
  });

  test("round-trip with empty values preserved", () => {
    const source = new Map<string, string>([
      ["serial", ""],
      ["description", ""],
      ["user", "alice"]
    ]);

    const fv = new FilterValue();
    fv.setFromMap(source);

    const parsed = fv.filterMap;
    expect(parsed.get("serial")).toBe("");
    expect(parsed.get("description")).toBe("");
    expect(parsed.get("user")).toBe("alice");
  });
});

describe("Edge cases", () => {
  test("trailing spaces do not affect parsing", () => {
    const fv = new FilterValue({ value: 'description:"this token is"   user:  alice   ' });
    expect(fv.filterMap.get("description")).toBe("this token is");
    expect(fv.filterMap.get("user")).toBe("alice");
  });

  test("values with quotes inside are preserved via setFromMap (escaped by serializer)", () => {
    const source = new Map<string, string>([
      ["description", `He said "hello"`],
      ["note", "it's fine"]
    ]);
    const fv = new FilterValue();
    fv.setFromMap(source);
    const parsed = fv.filterMap;
    expect(parsed.get("description")).toBe(`He said "hello"`);
    expect(parsed.get("note")).toBe("it's fine");
  });

  test("excludes asterisk-only values (wildcard means no filter)", () => {
    const fv = new FilterValue({
      value: `description:* user:alice version:"*" note:'*' realm:"**"`
    });

    expect(fv.filterMap.get("description")).toBeUndefined();
    expect(fv.filterMap.get("version")).toBeUndefined();
    expect(fv.filterMap.get("note")).toBeUndefined();

    expect(fv.filterMap.get("user")).toBe("alice");

    expect(fv.filterMap.get("realm")).toBe("**");

    const fvh = new FilterValue({
      hiddenValue: `serial:* container_serial:'*' keep:**`
    });
    expect(fvh.hiddenFilterMap.get("serial")).toBeUndefined();
    expect(fvh.hiddenFilterMap.get("container_serial")).toBeUndefined();
    expect(fvh.hiddenFilterMap.get("keep")).toBe("**");
  });

  test("setFromMap drops asterisk-only values", () => {
    const source = new Map<string, string>([
      ["description", "*"],
      ["user", "alice"],
    ]);
    const fv = new FilterValue();
    fv.setFromMap(source);
    expect(fv.filterMap.get("description")).toBeUndefined();
    expect(fv.filterMap.get("user")).toBe("alice");
  });
});
