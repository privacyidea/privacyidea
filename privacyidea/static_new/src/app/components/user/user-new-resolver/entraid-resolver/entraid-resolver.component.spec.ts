import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EntraidResolverComponent } from './entraid-resolver.component';

describe('EntraidResolverComponent', () => {
  let component: EntraidResolverComponent;
  let fixture: ComponentFixture<EntraidResolverComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EntraidResolverComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EntraidResolverComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
