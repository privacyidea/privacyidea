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
import { TestBed } from "@angular/core/testing";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { provideNoopAnimations } from "@angular/platform-browser/animations";
import { of } from "rxjs";

import { ContainerTabComponent } from "./container-tab.component";
import { ROUTE_PATHS } from "../../../../route_paths";
import { ContainerService } from "../../../../services/container/container.service";
import { ContentService } from "../../../../services/content/content.service";
import { VersioningService } from "../../../../services/version/version.service";
import { AuthService } from "../../../../services/auth/auth.service";
import { MatDialog } from "@angular/material/dialog";
import { ActivatedRoute, Router } from "@angular/router";
import { ConfirmationDialogComponent } from "../../../shared/confirmation-dialog/confirmation-dialog.component";
import {
  MockAuthService,
  MockContainerService,
  MockContentService,
  MockLocalService,
  MockNotificationService
} from "../../../../../testing/mock-services";

describe("ContainerTabComponent", () => {
  let component: ContainerTabComponent;
  let containerService: MockContainerService;
  let contentService: MockContentService;
  let router: jest.Mocked<Router>;
  let dialog: { open: jest.Mock };
  let versioning: { getVersion: jest.Mock };

  beforeEach(async () => {
    router = {
      navigateByUrl: jest.fn()
    } as any;

    dialog = {
      open: jest.fn().mockReturnValue({ afterClosed: () => of(true) })
    };

    versioning = {
      getVersion: jest.fn().mockReturnValue("1.2.3")
    };

    await TestBed.configureTestingModule({
      imports: [ContainerTabComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNoopAnimations(),
        {
          provide: ActivatedRoute,
          useValue: {
            params: of({ id: "123" })
          }
        },
        { provide: Router, useValue: router },
        { provide: MatDialog, useValue: dialog },
        { provide: ContainerService, useClass: MockContainerService },
        { provide: ContentService, useClass: MockContentService },
        { provide: VersioningService, useValue: versioning },
        { provide: AuthService, useClass: MockAuthService },
        MockLocalService,
        MockNotificationService
      ]
    }).compileComponents();

    const fixture = TestBed.createComponent(ContainerTabComponent);
    component = fixture.componentInstance;

    containerService = TestBed.inject(ContainerService) as any;
    contentService = TestBed.inject(ContentService) as any;

    fixture.detectChanges();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("ngOnInit should read version from VersioningService", () => {
    expect(versioning.getVersion).toHaveBeenCalled();
    expect(component.version).toBe("1.2.3");
  });

  it("containerIsSelected reflects containerSerial signal", () => {
    expect(component.containerIsSelected()).toBe(true);

    containerService.containerSerial.set("");
    expect(component.containerIsSelected()).toBe(false);

    containerService.containerSerial.set("CONT-42");
    expect(component.containerIsSelected()).toBe(true);
  });

  it("states computed reads from containerDetailResource", () => {
    expect(component.states()).toEqual([]);

    containerService.containerDetailResource.value.update((resp: any) => ({
      ...resp,
      result: {
        ...resp.result,
        value: {
          ...resp.result.value,
          containers: [
            {
              ...resp.result.value.containers[0],
              states: ["active", "locked"]
            }
          ]
        }
      }
    }));

    expect(component.states()).toEqual(["active", "locked"]);
  });

  it("onClickContainerOverview navigates to TOKENS_CONTAINERS", () => {
    component.onClickContainerOverview();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_CONTAINERS);
  });

  it("enrollTokenInContainer marks programmatic change, selects container, and navigates", () => {
    containerService.containerSerial.set("CONT-99");

    component.enrollTokenInContainer();

    expect(contentService.isProgrammaticTabChange()).toBe(true);
    expect(containerService.selectedContainer()).toBe("CONT-99");
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_ENROLLMENT);
  });

  it("toggleActive calls service and reloads container details", () => {
    const reloadSpy = containerService.containerDetailResource.reload as jest.Mock;
    containerService.containerSerial.set("CONT-1");

    containerService.containerDetailResource.value.update((resp: any) => ({
      ...resp,
      result: {
        ...resp.result,
        value: {
          ...resp.result.value,
          containers: [
            {
              ...resp.result.value.containers[0],
              states: ["active"]
            }
          ]
        }
      }
    }));

    component.toggleActive();

    expect(containerService.toggleActive).toHaveBeenCalledWith("CONT-1", ["active"]);
    expect(reloadSpy).toHaveBeenCalled();
  });

  it("deleteContainer opens confirm dialog, deletes, and navigates to TOKENS_CONTAINERS when previousUrl is not details", () => {
    (contentService as any).previousUrl = () => "/home";

    component.deleteContainer();

    expect(dialog.open).toHaveBeenCalledWith(ConfirmationDialogComponent, {
      data: {
        serialList: [containerService.containerSerial()],
        title: "Delete Container",
        type: "container",
        action: "delete",
        numberOfTokens: 1
      }
    });

    expect(containerService.deleteContainer).toHaveBeenCalledWith(containerService.containerSerial());
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.TOKENS_CONTAINERS);
  });

  it("deleteContainer navigates back to previous details page when previousUrl starts with TOKENS_DETAILS", () => {
    const prev = `${ROUTE_PATHS.TOKENS_DETAILS}/X`;
    (contentService as any).previousUrl = () => prev;

    component.deleteContainer();

    expect(containerService.deleteContainer).toHaveBeenCalledWith(containerService.containerSerial());
    expect(contentService.isProgrammaticTabChange()).toBe(true);
    expect(router.navigateByUrl).toHaveBeenCalledWith(prev);
  });

  it("deleteSelectedContainer opens confirm dialog, deletes all, clears selection and reloads list", () => {
    containerService.containerSelection.set([
      { serial: "C-1" } as any,
      { serial: "C-2" } as any
    ]);

    const listReloadSpy = containerService.containerResource.reload as jest.Mock;

    component.deleteSelectedContainer();

    expect(dialog.open).toHaveBeenCalledWith(ConfirmationDialogComponent, {
      data: {
        serialList: ["C-1", "C-2"],
        title: "Delete All Containers",
        type: "container",
        action: "delete",
        numberOfContainers: 2
      }
    });

    expect(containerService.deleteContainer).toHaveBeenCalledTimes(2);
    expect(containerService.deleteContainer).toHaveBeenNthCalledWith(1, "C-1");
    expect(containerService.deleteContainer).toHaveBeenNthCalledWith(2, "C-2");

    expect(containerService.containerSelection()).toEqual([]);
    expect(listReloadSpy).toHaveBeenCalled();
  });
});
