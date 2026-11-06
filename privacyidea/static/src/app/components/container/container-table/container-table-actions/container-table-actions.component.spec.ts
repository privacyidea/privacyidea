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
import { ContainerDetailData, ContainerService } from "@services/container/container.service";
import {
  MockContainerService,
  MockContentService,
  MockDocumentationService,
  MockPiResponse,
  MockTableUtilsService
} from "@testing/mock-services";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TableAction } from "@components/shared/table-actions/table-actions.component";
import { ContentService } from "@services/content/content.service";
import { DocumentationService } from "@services/documentation/documentation.service";
import { DialogService } from "@services/dialog/dialog.service";

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

  describe("deleteSelectedContainer", () => {
    function mockDialogResult(result: unknown): void {
      jest
        .spyOn((component as unknown as { dialogService: DialogService }).dialogService, "openDialog")
        .mockReturnValue({ afterClosed: () => of(result) } as ReturnType<DialogService["openDialog"]>);
    }

    it("deletes every selected container, clears the selection and reloads when confirmed", () => {
      const reloadSpy = jest.spyOn(containerService.containerResource, "reload");
      containerService.setContainerSelection([{ serial: "CONT-1" }, { serial: "CONT-2" }] as ContainerDetailData[]);
      mockDialogResult(true);

      component.deleteSelectedContainer();

      expect(containerService.deleteContainer).toHaveBeenCalledWith("CONT-1");
      expect(containerService.deleteContainer).toHaveBeenCalledWith("CONT-2");
      expect(containerService.containerSelection.hasSelection()).toBe(false);
      expect(reloadSpy).toHaveBeenCalled();
    });

    it("does nothing when the confirmation is dismissed", () => {
      containerService.setContainerSelection([{ serial: "CONT-1" }] as ContainerDetailData[]);
      mockDialogResult(false);

      component.deleteSelectedContainer();

      expect(containerService.deleteContainer).not.toHaveBeenCalled();
      expect(containerService.containerSelection.selectedCount()).toBe(1);
    });
  });

  describe("toggleComparison", () => {
    // The toolbar is rendered by app-table-actions from the action list, so the list is what is checked here.
    const compareAction = (): TableAction | undefined =>
      (component as unknown as { actions: () => TableAction[] }).actions().find((action) => action.id === "compare");

    it("enables the action without a selection", () => {
      expect(containerService.containerSelection.hasSelection()).toBe(false);
      expect(compareAction()?.label).toBe("Compare with templates");
      expect(compareAction()?.disabled).toBe(false);
    });

    it("emits the comparison results of all containers on the page", async () => {
      const selected = [
        { serial: "CONT-1", template: "baseline" },
        { serial: "CONT-2", template: "" }
      ] as ContainerDetailData[];
      containerService.containerResource.set(MockPiResponse.fromValue({ containers: selected, count: 2 }));
      const comparisons = [
        {
          additional: [],
          containerSerial: "CONT-1",
          equal: true,
          missing: [],
          templateName: "baseline"
        }
      ];
      containerService.compareContainersWithTemplates.mockResolvedValue(comparisons);
      const loadedSpy = jest.fn();
      component.comparisonLoaded.subscribe(loadedSpy);

      await component.toggleComparison();

      expect(containerService.compareContainersWithTemplates).toHaveBeenCalledWith(selected);
      expect(loadedSpy).toHaveBeenCalledWith(comparisons);
    });

    it("emits comparisonHidden instead of comparing while the comparison is shown", async () => {
      fixture.componentRef.setInput("comparisonActive", true);
      const hiddenSpy = jest.fn();
      component.comparisonHidden.subscribe(hiddenSpy);

      await component.toggleComparison();

      expect(hiddenSpy).toHaveBeenCalledTimes(1);
      expect(containerService.compareContainersWithTemplates).not.toHaveBeenCalled();
    });

    it("labels the action to hide the comparison while it is shown", () => {
      fixture.componentRef.setInput("comparisonActive", true);
      fixture.detectChanges();

      expect(compareAction()?.label).toBe("Hide comparison");
    });

    it("reports comparison errors", async () => {
      containerService.containerResource.set(
        MockPiResponse.fromValue({ containers: [{ serial: "CONT-1" }] as ContainerDetailData[], count: 1 })
      );
      containerService.compareContainersWithTemplates.mockRejectedValue(new Error("Comparison failed"));
      const errorSpy = jest.spyOn(
        (component as unknown as { notificationService: { error: (msg: string) => void } }).notificationService,
        "error"
      );
      jest.spyOn(console, "error").mockImplementation();

      await component.toggleComparison();

      expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining("Comparison failed"));
    });
  });

  describe("getFilterIconName", () => {
    it("returns filter_alt for 'assigned' when no value is set", () => {
      containerService.activeFilter.set(new FilterValue());
      expect(component.getFilterIconName("assigned")).toBe("filter_alt");
    });

    it("returns screen_rotation_alt for 'assigned' when value is 'true'", () => {
      containerService.activeFilter.set(new FilterValue({ value: "assigned: true" }));
      expect(component.getFilterIconName("assigned")).toBe("screen_rotation_alt");
    });

    it("returns filter_alt_off for 'assigned' when value is 'false'", () => {
      containerService.activeFilter.set(new FilterValue({ value: "assigned: false" }));
      expect(component.getFilterIconName("assigned")).toBe("filter_alt_off");
    });

    it("returns filter_alt_off for a non-assigned keyword that is present in the filter", () => {
      containerService.activeFilter.set(new FilterValue({ value: "type: " }));
      expect(component.getFilterIconName("type")).toBe("filter_alt_off");
    });

    it("returns filter_alt for a non-assigned keyword that is not in the filter", () => {
      containerService.activeFilter.set(new FilterValue());
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
      const initialFilter = containerService.activeFilter();
      const newFilter = new FilterValue({ value: "assigned: true" });
      tableUtilsService.toggleBooleanInFilter.mockReturnValue(newFilter);
      const setSpy = jest.spyOn(containerService.activeFilter, "set");
      const openMenu = jest.fn();
      jest
        .spyOn(component, "advancedFilterTrigger")
        .mockReturnValue({ openMenu } as Partial<MatMenuTrigger> as MatMenuTrigger);

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
      const initialFilter = containerService.activeFilter();
      const newFilter = new FilterValue({ value: "type: " });
      tableUtilsService.toggleKeywordInFilter.mockReturnValue(newFilter);
      const setSpy = jest.spyOn(containerService.activeFilter, "set");
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
