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
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { UserTableActionsComponent } from "./user-table-actions.component";
import { DialogService } from "../../../../services/dialog/dialog.service";
import { UserService } from "../../../../services/user/user.service";
import { ResolverService } from "../../../../services/resolver/resolver.service";
import { MockResolverService } from "../../../../../testing/mock-services/mock-resolver-service";
import { MockDialogService, MockUserService } from "../../../../../testing/mock-services";



describe("UserTableActionsComponent", () => {
  let component: UserTableActionsComponent;
  let fixture: ComponentFixture<UserTableActionsComponent>;
  let resolverService: MockResolverService;
  let userService: MockUserService;
  let dialogService: MockDialogService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ResolverService, useClass: MockResolverService },
        { provide: UserService, useClass: MockUserService },
        { provide: DialogService, useClass: MockDialogService }
      ],
      imports: [UserTableActionsComponent]
    }).compileComponents();

    resolverService = TestBed.inject(ResolverService) as unknown as MockResolverService;
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    dialogService = TestBed.inject(DialogService) as unknown as MockDialogService;

    fixture = TestBed.createComponent(UserTableActionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("anyEditableResolver returns true if editableResolvers is non-empty", () => {
    resolverService.editableResolvers.set(["resolver1"]);
    expect(component.anyEditableResolver()).toBe(true);
  });

  it("anyEditableResolver returns false if editableResolvers is empty", () => {
    resolverService.editableResolvers.set([]);
    expect(component.anyEditableResolver()).toBe(false);
  });

  it("openCreateUserDialog calls dialogService.openDialog with correct data", () => {
    userService.selectedUserRealm.set("testRealm");
    component.openCreateUserDialog();
    expect(dialogService.openDialog).toHaveBeenCalledWith(
      expect.objectContaining({
        component: expect.anything(),
        data: { realm: "testRealm" }
      })
    );
  });
});
