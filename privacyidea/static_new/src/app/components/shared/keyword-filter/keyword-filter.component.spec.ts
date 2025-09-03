import { ComponentFixture, TestBed } from "@angular/core/testing";
import { signal } from "@angular/core";

import { KeywordFilterComponent } from "./keyword-filter.component";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { FilterValue } from "../../../core/models/filter_value";

class MockTableUtilsService {
  toggleBooleanInFilter = jest.fn();
  toggleKeywordInFilter = jest.fn();
}

function setupComponent(): {
  fixture: ComponentFixture<KeywordFilterComponent>;
  component: KeywordFilterComponent;
  mockTableUtilsService: jest.Mocked<MockTableUtilsService>;
} {
  const mockTableUtilsService = new MockTableUtilsService() as jest.Mocked<MockTableUtilsService>;
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({
    imports: [KeywordFilterComponent],
    providers: [{ provide: TableUtilsService, useValue: mockTableUtilsService }]
  }).compileComponents();

  const fixture = TestBed.createComponent(KeywordFilterComponent);
  const component = fixture.componentInstance;

  component.apiFilter = ["active", "host", "infokey & infovalue"];
  component.advancedApiFilter = ["machineid & resolver"];
  component.filterHTMLInputElement = document.createElement("input");
  component.filterHTMLInputElement.focus = jest.fn();

  component.filterValue = signal<FilterValue>(new FilterValue());
  component.showAdvancedFilter = signal(false);

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
    `('returns $expected when value="$stored"', ({ stored, expected }) => {
      const current = stored ? new FilterValue({ value: `active:${stored}` }) : new FilterValue({ value: "active: " });
      component.filterValue.set(current);
      fixture.detectChanges();
      expect(component.getFilterIconName("active")).toBe(expected);
    });
  });

  describe("getFilterIconName", () => {
    it("returns remove_circle if keyword is already present", () => {
      component.filterValue.set(new FilterValue({ value: "host: abc" }));
      fixture.detectChanges();
      const icon = component.getFilterIconName("host");
      expect(icon).toBe("remove_circle");
    });

    it("returns add_circle if keyword not present", () => {
      component.filterValue.set(new FilterValue());
      fixture.detectChanges();
      const icon = component.getFilterIconName("host");
      expect(icon).toBe("add_circle");
    });
  });

  describe("isFilterSelected", () => {
    it.each([
      ["infokey & infovalue", new FilterValue({ value: "infokey: x" })],
      ["infokey & infovalue", new FilterValue({ value: "infovalue: y" })],
      ["machineid & resolver", new FilterValue({ value: "machineid: z" })]
    ])('detects group keyword "%s"', (kw, value) => {
      expect(component.isFilterSelected(kw, value)).toBe(true);
    });

    it("handles normal keyword", () => {
      expect(component.isFilterSelected("host", new FilterValue({ value: "host: abc" }))).toBe(true);
      expect(component.isFilterSelected("host", new FilterValue())).toBe(false);
    });
  });

  describe("toggleFilter", () => {
    beforeEach(() => {
      component.filterHTMLInputElement.value = "";
    });

    it("uses toggleBooleanInFilter for boolean keywords", () => {
      mockSvc.toggleBooleanInFilter.mockRejectedValue(new FilterValue({ value: "active:true" }));
      component.filterValue.set(new FilterValue());
      fixture.detectChanges();

      component.toggleFilter("active");

      expect(mockSvc.toggleBooleanInFilter).toHaveBeenCalledWith({
        keyword: "active",
        currentValue: new FilterValue()
      });
      fixture.detectChanges();
      expect(component.filterHTMLInputElement.value).toBe("active:true");
      expect(component.filterValue()).toEqual({ active: "true" });
      expect(component.filterHTMLInputElement.focus).toHaveBeenCalled();
    });

    it("uses toggleKeywordInFilter for non‑boolean keywords", () => {
      mockSvc.toggleKeywordInFilter.mockRejectedValue(new FilterValue({ value: "host:abc" }));

      component.toggleFilter("host");

      expect(mockSvc.toggleKeywordInFilter).toHaveBeenCalledWith({
        keyword: "host",
        currentValue: new FilterValue()
      });

      /// Wait for signals to propagate
      fixture.detectChanges();
      expect(component.filterHTMLInputElement.value).toBe("host:abc");
      expect(component.filterValue()).toEqual({ host: "abc" });
      expect(component.filterHTMLInputElement.focus).toHaveBeenCalled();
    });
  });

  it("delegates to toggleFilter with current input element", () => {
    const spy = jest.spyOn(component, "toggleFilter");
    component.onKeywordClick("host");
    expect(spy).toHaveBeenCalledWith("host");
  });
});
