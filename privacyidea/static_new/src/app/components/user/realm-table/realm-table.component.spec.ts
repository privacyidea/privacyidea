import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RealmsComponent } from './realm-table.component';

describe('RealmsComponent', () => {
  let component: RealmsComponent;
  let fixture: ComponentFixture<RealmsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RealmsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(RealmsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
