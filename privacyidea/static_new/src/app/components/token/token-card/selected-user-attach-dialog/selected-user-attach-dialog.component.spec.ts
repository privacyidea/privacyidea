import { ComponentFixture, TestBed } from "@angular/core/testing";

import { SelectedUserAssignDialogComponent } from "./selected-user-attach-dialog.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MatDialogRef } from "@angular/material/dialog";

describe("SelectedUserAssignDialogComponent", () => {
  let component: SelectedUserAssignDialogComponent;
  let fixture: ComponentFixture<SelectedUserAssignDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SelectedUserAssignDialogComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: MatDialogRef, useValue: { close: jest.fn() } }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(SelectedUserAssignDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
