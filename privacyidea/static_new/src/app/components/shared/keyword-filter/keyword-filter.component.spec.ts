/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { signal } from "@angular/core";
import { KeywordFilterComponent } from "./keyword-filter.component";
import { TableUtilsService } from "../../../services/table-utils/table-utils.service";
import { FilterValue } from "../../../core/models/filter_value";
import { MockTableUtilsService } from "../../../../testing/mock-services";
function setupComponent(): {
  fixture: ComponentFixture<KeywordFilterComponent>;
  component: KeywordFilterComponent;
  mockTableUtilsService: jest.Mocked<MockTableUtilsService>;
} {
  TestBed.resetTestingModule();
  TestBed.configureTestingModule({
    imports: [KeywordFilterComponent],
    providers: [{ provide: TableUtilsService, useClass: MockTableUtilsService }]
  }).compileComponents();
  const fixture = TestBed.createComponent(KeywordFilterComponent);
  const component = fixture.componentInstance;
  component.apiFilter = ["active", "host", "infokey & infovalue"];
  component.advancedApiFilter = ["machineid & resolver"];
  component.filterHTMLInputElement = document.createElement("input");
  component.filterHTMLInputElement.focus = jest.fn();
  component.filterValue = signal<FilterValue>(new FilterValue());
  component.showAdvancedFilter = signal(false);
  const mockTableUtilsService = TestBed.inject(TableUtilsService) as unknown as jest.Mocked<MockTableUtilsService>;
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
    it("uses toggleBooleanInFilter for boolean keywords", async () => {
      mockSvc.toggleBooleanInFilter.mockReturnValue(new FilterValue({ value: "active:true" }));
      component.filterValue.set(new FilterValue());
      fixture.detectChanges();
      component.toggleFilter("active");
      fixture.detectChanges();
      expect(mockSvc.toggleBooleanInFilter).toHaveBeenCalledWith({
        keyword: "active",
        currentValue: new FilterValue()
      });
      fixture.detectChanges();
      expect(component.filterValue().value).toEqual("active:true");
      expect(component.filterHTMLInputElement.focus).toHaveBeenCalled();
    });
    it("uses toggleKeywordInFilter for non‑boolean keywords", async () => {
      mockSvc.toggleKeywordInFilter.mockReturnValue(new FilterValue({ value: "host:abc" }));
      component.toggleFilter("host");
      expect(mockSvc.toggleKeywordInFilter).toHaveBeenCalledWith({
        keyword: "host",
        currentValue: new FilterValue()
      });
      /// Wait for signals to propagate
      fixture.detectChanges();
      expect(component.filterValue().value).toEqual("host:abc");
      expect(component.filterHTMLInputElement.focus).toHaveBeenCalled();
    });
  });
  it("delegates to toggleFilter with current input element", () => {
    const spy = jest.spyOn(component, "toggleFilter");
    component.onKeywordClick("host");
    expect(spy).toHaveBeenCalledWith("host");
  });
});
