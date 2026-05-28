/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
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
import { MatMenuTrigger } from "@angular/material/menu";

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ActivatedRoute } from "@angular/router";
import { FilterValue } from "@core/models/filter_value/filter_value";
import { of } from "rxjs";
import { ContainerTableActionsComponent } from "./container-table-actions.component";
import { ContainerService } from "@services/container/container.service";
import {
  MockContainerService,
  MockContentService,
  MockDocumentationService,
  MockTableUtilsService
} from "@testing/mock-services";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { ContentService } from "@services/content/content.service";
import { DocumentationService } from "@services/documentation/documentation.service";

describe("ContainerTableActionsComponent", () => {
  let component: ContainerTableActionsComponent;
  let fixture: ComponentFixture<ContainerTableActionsComponent>;
  let containerService: MockContainerService;
  let tableUtilsService: MockTableUtilsService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { params: of({ id: "123" }) }
        },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: TableUtilsService, useClass: MockTableUtilsService },
        { provide: ContentService, useClass: MockContentService },
        { provide: DocumentationService, useClass: MockDocumentationService }
      ],
      imports: [ContainerTableActionsComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTableActionsComponent);
    component = fixture.componentInstance;
    containerService = TestBed.inject(ContainerService) as unknown as MockContainerService;
    tableUtilsService = TestBed.inject(TableUtilsService) as unknown as MockTableUtilsService;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("getFilterIconName", () => {
    it("returns filter_alt for 'assigned' when no value is set", () => {
      containerService.containerFilter.set(new FilterValue());
      expect(component.getFilterIconName("assigned")).toBe("filter_alt");
    });

    it("returns screen_rotation_alt for 'assigned' when value is 'true'", () => {
      containerService.containerFilter.set(new FilterValue({ value: "assigned: true" }));
      expect(component.getFilterIconName("assigned")).toBe("screen_rotation_alt");
    });

    it("returns filter_alt_off for 'assigned' when value is 'false'", () => {
      containerService.containerFilter.set(new FilterValue({ value: "assigned: false" }));
      expect(component.getFilterIconName("assigned")).toBe("filter_alt_off");
    });

    it("returns filter_alt_off for a non-assigned keyword that is present in the filter", () => {
      containerService.containerFilter.set(new FilterValue({ value: "type: " }));
      expect(component.getFilterIconName("type")).toBe("filter_alt_off");
    });

    it("returns filter_alt for a non-assigned keyword that is not in the filter", () => {
      containerService.containerFilter.set(new FilterValue());
      expect(component.getFilterIconName("type")).toBe("filter_alt");
    });
  });

  describe("onAdvancedFilterClick", () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.useRealTimers();
    });

    it("toggles boolean filter and reopens the menu for 'assigned'", () => {
      const initialFilter = containerService.containerFilter();
      const newFilter = new FilterValue({ value: "assigned: true" });
      tableUtilsService.toggleBooleanInFilter.mockReturnValue(newFilter);
      const setSpy = jest.spyOn(containerService.containerFilter, "set");
      const openMenu = jest.fn();
      jest.spyOn(component, "advancedFilterTrigger").mockReturnValue({ openMenu } as Partial<MatMenuTrigger> as MatMenuTrigger);

      component.onAdvancedFilterClick("assigned");

      expect(tableUtilsService.toggleBooleanInFilter).toHaveBeenCalledWith({
        keyword: "assigned",
        currentValue: initialFilter
      });
      expect(tableUtilsService.toggleKeywordInFilter).not.toHaveBeenCalled();
      expect(setSpy).toHaveBeenCalledWith(newFilter);

      jest.runAllTimers();
      expect(openMenu).toHaveBeenCalled();
    });

    it("toggles keyword filter and focuses the filter input for non-assigned keywords", () => {
      const initialFilter = containerService.containerFilter();
      const newFilter = new FilterValue({ value: "type: " });
      tableUtilsService.toggleKeywordInFilter.mockReturnValue(newFilter);
      const setSpy = jest.spyOn(containerService.containerFilter, "set");
      const focus = jest.fn();
      const getElementByIdSpy = jest
        .spyOn(document, "getElementById")
        .mockReturnValue({ focus } as unknown as HTMLInputElement);

      component.onAdvancedFilterClick("type");

      expect(tableUtilsService.toggleKeywordInFilter).toHaveBeenCalledWith({
        keyword: "type",
        currentValue: initialFilter
      });
      expect(tableUtilsService.toggleBooleanInFilter).not.toHaveBeenCalled();
      expect(setSpy).toHaveBeenCalledWith(newFilter);

      jest.runAllTimers();
      expect(getElementByIdSpy).toHaveBeenCalledWith("container-filter-input");
      expect(focus).toHaveBeenCalled();
    });

    it("safely handles a missing filter input element", () => {
      tableUtilsService.toggleKeywordInFilter.mockReturnValue(new FilterValue());
      jest.spyOn(document, "getElementById").mockReturnValue(null);

      expect(() => {
        component.onAdvancedFilterClick("type");
        jest.runAllTimers();
      }).not.toThrow();
    });
  });
});
