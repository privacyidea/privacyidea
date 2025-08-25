import { ComponentFixture, TestBed } from "@angular/core/testing";

import { ResyncTokenActionComponent } from "./resync-token-action.component";

describe("ResyncTokenActionComponent", () => {
  let component: ResyncTokenActionComponent;
  let fixture: ComponentFixture<ResyncTokenActionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ResyncTokenActionComponent]
    })
      .compileComponents();

    fixture = TestBed.createComponent(ResyncTokenActionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
