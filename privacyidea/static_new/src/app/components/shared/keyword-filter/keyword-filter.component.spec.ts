import { ComponentFixture, TestBed } from "@angular/core/testing";
import { signal } from "@angular/core";

import { KeywordFilterComponent } from "./keyword-filter.component";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";

class MockTableUtilsService {
  toggleBooleanInFilter = jest.fn();
  toggleKeywordInFilter = jest.fn();
  recordsFromText = jest.fn();
}

function setupComponent(): {
  fixture: ComponentFixture<KeywordFilterComponent>;
  component: KeywordFilterComponent;
  mockTableUtilsService: jest.Mocked<MockTableUtilsService>;
} {
  const mockTableUtilsService =
    new MockTableUtilsService() as jest.Mocked<MockTableUtilsService>;
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({
    imports: [KeywordFilterComponent],
    providers: [
      { provide: TableUtilsService, useValue: mockTableUtilsService }
    ]
  }).compileComponents();

  const fixture = TestBed.createComponent(KeywordFilterComponent);
  const component = fixture.componentInstance;

  component.filterHTMLInputElement = document.createElement("input");
  component.filterHTMLInputElement.focus = jest.fn();
  component.filterValue = signal<Record<string, string>>({});
  component.apiFilter = ["active", "host", "infokey & infovalue"];
  component.advancedApiFilter = ["machineid & resolver"];

  fixture.detectChanges();
  return { fixture, component, mockTableUtilsService: mockTableUtilsService };
}

describe("KeywordFilterComponent", () => {
  let fixture: ComponentFixture<KeywordFilterComponent>;
  let component: KeywordFilterComponent;
  let mockSvc: jest.Mocked<MockTableUtilsService>;

  beforeEach(async () => {
    const setup = setupComponent();
    fixture = setup.fixture;
    component = setup.component;
    mockSvc = setup.mockTableUtilsService;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("getFilterIconName", () => {
    it.each`
      stored       | expected
      ${undefined} | ${"add_circle"}
      ${"TrUe"}    | ${"change_circle"}
      ${"false"}   | ${"remove_circle"}
    `("returns $expected when value=\"$stored\"", ({ stored, expected }) => {
      const current = stored ? { active: stored as string } : { active: "" };
      expect(component.getFilterIconName("active", current)).toBe(expected);
    });
  });

  describe("getFilterIconName", () => {
    it("returns remove_circle if keyword is already present", () => {
      const icon = component.getFilterIconName("host", { host: "abc" });
      expect(icon).toBe("remove_circle");
    });

    it("returns add_circle if keyword not present", () => {
      const icon = component.getFilterIconName("host", {});
      expect(icon).toBe("add_circle");
    });
  });

  describe("isFilterSelected", () => {
    it.each([
      ["infokey & infovalue", { infokey: "x" }],
      ["infokey & infovalue", { infovalue: "y" }],
      ["machineid & resolver", { resolver: "z" }]
    ])("detects group keyword \"%s\"", (kw, value) => {
      expect(component.isFilterSelected(kw, value)).toBe(true);
    });

    it("handles normal keyword", () => {
      expect(component.isFilterSelected("host", { host: "abc" })).toBe(true);
      expect(component.isFilterSelected("host", {})).toBe(false);
    });
  });

  describe("toggleFilter", () => {
    beforeEach(() => {
      component.filterHTMLInputElement.value = "";
    });

    it("uses toggleBooleanInFilter for boolean keywords", () => {
      mockSvc.toggleBooleanInFilter.mockReturnValue("active:true");
      mockSvc.recordsFromText.mockReturnValue({ active: "true" });

      component.toggleFilter("active", component.filterHTMLInputElement);

      expect(mockSvc.toggleBooleanInFilter).toHaveBeenCalledWith({
        keyword: "active",
        currentValue: ""
      });
      expect(component.filterHTMLInputElement.value).toBe("active:true");
      expect(component.filterValue()).toEqual({ active: "true" });
      expect(component.filterHTMLInputElement.focus).toHaveBeenCalled();
    });

    it("uses toggleKeywordInFilter for non‑boolean keywords", () => {
      mockSvc.toggleKeywordInFilter.mockReturnValue("host:abc");
      mockSvc.recordsFromText.mockReturnValue({ host: "abc" });

      component.toggleFilter("host", component.filterHTMLInputElement);

      expect(mockSvc.toggleKeywordInFilter).toHaveBeenCalledWith("", "host");
      expect(component.filterHTMLInputElement.value).toBe("host:abc");
      expect(component.filterValue()).toEqual({ host: "abc" });
      expect(component.filterHTMLInputElement.focus).toHaveBeenCalled();
    });
  });

  it("delegates to toggleFilter with current input element", () => {
    const spy = jest.spyOn(component, "toggleFilter");
    component.onKeywordClick("host");
    expect(spy).toHaveBeenCalledWith("host", component.filterHTMLInputElement);
  });

  describe("filterIsEmpty", () => {
    it("is true when both text and signal are empty", () => {
      component.filterHTMLInputElement.value = "";
      component.filterValue.set({});
      expect(component.filterIsEmpty()).toBe(true);
    });

    it("is false when text is non‑empty", () => {
      component.filterHTMLInputElement.value = "foo";
      expect(component.filterIsEmpty()).toBe(false);
    });

    it("is false when signal contains data", () => {
      component.filterHTMLInputElement.value = "";
      component.filterValue.set({ host: "abc" });
      expect(component.filterIsEmpty()).toBe(false);
    });
  });
});
