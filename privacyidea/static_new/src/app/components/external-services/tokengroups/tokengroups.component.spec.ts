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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { Router, provideRouter } from "@angular/router";
import { ROUTE_PATHS } from "@app/route_paths";
import { SaveAndExitDialogResult } from "@components/shared/dialog/save-and-exit-dialog/save-and-exit-dialog.component";
import { AuthService } from "@services/auth/auth.service";
import { DialogService } from "@services/dialog/dialog.service";
import { TableUtilsService } from "@services/table-utils/table-utils.service";
import { TokengroupService } from "@services/tokengroup/tokengroup.service";
import { MockMatDialogRef } from "@testing/mock-mat-dialog-ref";
import { MockAuthService, MockDialogService, MockTableUtilsService } from "@testing/mock-services";
import { Subject } from "rxjs";
import { TokengroupsComponent } from "./tokengroups.component";

describe("TokengroupsComponent", () => {
  let component: TokengroupsComponent;
  let fixture: ComponentFixture<TokengroupsComponent>;
  let tokengroupServiceMock: any;
  let dialogServiceMock: MockDialogService;
  let confirmClosed: Subject<SaveAndExitDialogResult>;
  let router: Router;

  beforeEach(async () => {
    tokengroupServiceMock = {
      tokengroups: signal([
        { groupname: "group1", description: "desc1", id: 1 },
        { groupname: "group2", description: "desc2", id: 2 }
      ]),
      deleteTokengroup: jest.fn()
    };

    await TestBed.configureTestingModule({
      imports: [TokengroupsComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: TokengroupService, useValue: tokengroupServiceMock },
        { provide: AuthService, useClass: MockAuthService },
        { provide: DialogService, useClass: MockDialogService },
        { provide: TableUtilsService, useClass: MockTableUtilsService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TokengroupsComponent);
    dialogServiceMock = TestBed.inject(DialogService) as unknown as MockDialogService;
    router = TestBed.inject(Router);
    jest.spyOn(router, "navigateByUrl").mockResolvedValue(true);
    confirmClosed = new Subject();
    let dialogRefMock = new MockMatDialogRef();
    dialogRefMock.afterClosed.mockReturnValue(confirmClosed);
    dialogServiceMock.openDialog.mockReturnValue(dialogRefMock);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display groups from service", () => {
    expect(component.tokengroupDataSource().data.length).toBe(2);
    expect(component.tokengroupDataSource().data[0].groupname).toBe("group1");
  });

  it("should filter groups", () => {
    component.onFilterInput("group1");
    expect(component.tokengroupDataSource().filter).toBe("group1");
  });

  it("should navigate to create page", () => {
    component.onCreateNewTokengroup();
    expect(router.navigateByUrl).toHaveBeenCalledWith(ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS_NEW);
  });

  it("should navigate to edit page when editing a group", () => {
    const group = tokengroupServiceMock.tokengroups()[0];
    component.onEditTokengroup(group);
    expect(router.navigateByUrl).toHaveBeenCalledWith(
      ROUTE_PATHS.EXTERNAL_SERVICES_TOKENGROUPS_DETAILS + group.groupname
    );
  });

  it("should delete group after confirmation", () => {
    const group = tokengroupServiceMock.tokengroups()[0];
    component.deleteTokengroup(group);
    expect(dialogServiceMock.openDialog).toHaveBeenCalled();
    confirmClosed.next("discard");
    confirmClosed.complete();
    expect(tokengroupServiceMock.deleteTokengroup).toHaveBeenCalledWith("group1");
  });
});
