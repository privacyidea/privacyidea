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
