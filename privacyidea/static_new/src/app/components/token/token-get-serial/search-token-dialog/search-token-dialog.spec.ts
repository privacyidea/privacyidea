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
import { SearchTokenDialogComponent } from "./search-token-dialog";
import { MAT_DIALOG_DATA, MatDialogRef } from "@angular/material/dialog";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockMatDialogRef } from "../../../../../testing/mock-mat-dialog-ref";

describe("SearchTokenDialogComponent", () => {
  let component: SearchTokenDialogComponent;
  let fixture: ComponentFixture<SearchTokenDialogComponent>;
  let mockDialogRef: MockMatDialogRef<SearchTokenDialogComponent, any>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule, SearchTokenDialogComponent],
      providers: [
        { provide: MatDialogRef, useClass: MockMatDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: 100 }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SearchTokenDialogComponent);
    mockDialogRef = TestBed.inject(MatDialogRef) as unknown as MockMatDialogRef<SearchTokenDialogComponent, any>;
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("should display the correct token count", () => {
    const p = fixture.nativeElement.querySelector("p");
    expect(p.textContent).toContain("100 tokens");
  });

  it("should close the dialog when the close button is clicked", () => {
    const button = fixture.nativeElement.querySelector("button");
    button.click();
    fixture.detectChanges();
    expect(mockDialogRef.close).toHaveBeenCalled();
  });
});
