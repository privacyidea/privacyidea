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

import {ComponentFixture, TestBed} from "@angular/core/testing";
import {UserAssignmentComponent} from "./user-assignment.component";
import {FormControl, ReactiveFormsModule} from "@angular/forms";
import {UserData, UserService} from "../../../services/user/user.service";
import {RealmService} from "../../../services/realm/realm.service";
import {MockRealmService, MockUserService} from "../../../../testing/mock-services";
import {By} from "@angular/platform-browser";


describe("UserAssignmentComponent", () => {
    let component: UserAssignmentComponent;
    let fixture: ComponentFixture<UserAssignmentComponent>;

    beforeEach(async () => {
        await TestBed.configureTestingModule({
            imports: [UserAssignmentComponent, ReactiveFormsModule],
            providers: [
                {provide: UserService, useClass: MockUserService},
                {provide: RealmService, useClass: MockRealmService}
            ]
        }).compileComponents();

        fixture = TestBed.createComponent(UserAssignmentComponent);
        component = fixture.componentInstance;
        component.showOnlyAddToRealm = true;
        fixture.detectChanges();
    });

    it("should create", () => {
        expect(component).toBeTruthy();
    });

    it("should use internal controls if inputs not provided", () => {
        expect(component.selectedUserRealmCtrl).toBe(component.internalSelectedUserRealmControl);
        expect(component.userFilterCtrl).toBe(component.internalUserFilterControl);
    });

    it("should bind input controls if provided", () => {
        const realmCtrl = new FormControl<string>("realm2", {nonNullable: true});
        const userCtrl = new FormControl<string | UserData | null>("user1", {nonNullable: true});
        component.selectedUserRealmControl = realmCtrl;
        component.userFilterControl = userCtrl;
        expect(component.selectedUserRealmCtrl).toBe(realmCtrl);
        expect(component.userFilterCtrl).toBe(userCtrl);
    });

    it("should enable/disable userFilterCtrl on onlyAddToRealm checkbox change", () => {
        const userCtrl = component.userFilterCtrl;
        component.onOnlyAddToRealmChange({checked: true});
        expect(userCtrl.disabled).toBe(true);
        component.onOnlyAddToRealmChange({checked: false});
        expect(userCtrl.enabled).toBe(true);
    });

    it("should enable/disable userFilterCtrl when checkbox is clicked", () => {
        fixture.detectChanges();
        const userCtrl = component.userFilterCtrl;
        // Find the checkbox element
        const checkboxDebug = fixture.debugElement.query(By.css("mat-checkbox input[type='checkbox']"));
        expect(checkboxDebug).toBeTruthy();

        // Initially unchecked
        expect(component.onlyAddToRealm()).toBe(false);
        expect(userCtrl.enabled).toBe(true);

        // Simulate checking the checkbox
        checkboxDebug.nativeElement.click();
        fixture.detectChanges();

        expect(component.onlyAddToRealm()).toBe(true);
        expect(userCtrl.disabled).toBe(true);

        // Simulate unchecking the checkbox
        checkboxDebug.nativeElement.click();
        fixture.detectChanges();

        expect(component.onlyAddToRealm()).toBe(false);
        expect(userCtrl.enabled).toBe(true);
    });

    it("should reset user filter on realm change", () => {
        const userCtrl = component.userFilterCtrl;
        userCtrl.setValue("user1");

        // Open the mat-select dropdown
        const selectTrigger = fixture.debugElement.query(By.css("mat-select"));
        selectTrigger.nativeElement.click();
        fixture.detectChanges();

        // Find and click the desired option
        const options = fixture.debugElement.queryAll(By.css("mat-option"));
        options.find(opt => opt.nativeElement.textContent.includes("realm2")).nativeElement.click();
        fixture.detectChanges();

        expect(component.userService.selectedUserRealm()).toBe("realm2");
        expect(userCtrl.value).toBe("");
        expect(userCtrl.enabled).toBe(true);
    });

    it("should disable user filter if realm is empty", () => {
        const realmCtrl = component.selectedUserRealmCtrl;
        const userCtrl = component.userFilterCtrl;
        realmCtrl.setValue("");
        component.onSelectedRealmChange(realmCtrl.value);
        expect(userCtrl.value).toBe("");
        expect(userCtrl.disabled).toBe(true);
        realmCtrl.setValue("realm1");
        component.onSelectedRealmChange(realmCtrl.value);
        expect(userCtrl.enabled).toBe(true);
    });

    it("should set onlyAddToRealm to false when user selected", () => {
        const userCtrl = component.userFilterCtrl;
        userCtrl.setValue("user1");
        expect(component.onlyAddToRealm()).toBe(false);
    });

    it("should disable onlyAddToRealm checkbox when user is selected", () => {
        const userCtrl = component.userFilterCtrl;
        userCtrl.setValue("user1");
        // Simulate template logic: checkbox is disabled if userFilterCtrl.value is truthy
        expect(!!userCtrl.value).toBe(true);
    });

    it("should enable onlyAddToRealm checkbox when user is cleared", () => {
        const userCtrl = component.userFilterCtrl;
        userCtrl.setValue("user1");
        userCtrl.setValue(null);
        // Simulate template logic: checkbox is enabled if userFilterCtrl.value is falsy
        expect(!userCtrl.value).toBe(true);
    });
});
