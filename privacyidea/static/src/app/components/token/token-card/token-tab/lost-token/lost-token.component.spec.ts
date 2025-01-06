import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LostTokenComponent } from './lost-token.component';

describe('LostTokenComponent', () => {
  let component: LostTokenComponent;
  let fixture: ComponentFixture<LostTokenComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LostTokenComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LostTokenComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
